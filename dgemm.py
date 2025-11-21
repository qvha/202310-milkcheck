#!/usr/bin/python3
# parses the output of :
# LD_LIBRARY_PATH=/usr/local/BenchElem/lib_intel64 /outils/bb8/repo/oneapi/vtune/latest/bin64/amplxe-perf stat --iostat=upi /usr/local/BenchElem/spr_linux_icx/dgemm -r 2 -t 8 -c 0 -x 1

debug=False

import os 
import sys
import argparse
import statistics


def init():
  parser = argparse.ArgumentParser(description="Parses the output of amplxe-perf stat dgemm, checks if "
           "everything is alright, warns about problems.",
           epilog="(c) 2025 BULL SAS, "
                  "HA Quoc Viet quoc-viet.ha@eviden.com>" )
  parser.add_argument("--sockets", "-s", metavar="<integer>", action="store",
           default=2, type=int,
           help="Number of sockets. This should match reality. "
           "Example on a single module : --sockets 2. Defaults to 2.")
  parser.add_argument("--upis",    "-u", metavar="<integer>", action="store",
           default=4, type=int,
           help="Number of UPI links per socket. This should match the intel architecture. "
           "Example on a Sapphire Rapids : --upis 4. Defaults to 4.")
  parser.add_argument("--down-links","-d", metavar="<s-u:s-u,..>", action="store",
           default=None, 
           help="specifies which link is down. If the link socket 0 upi 1 to socket 1 upi 0 is down: " 
           " -d 0-1:0-1. Use a comma to list more")
  parser.add_argument("--down-ports","-p", metavar="<s-u,s-u,..>", action="store",
           default=None, 
           help="specifies which port of which socket is down. If the upi port 3 is down on socket 0 : " 
           " -p 0-3. Use a comma to list more")

  parser.add_argument("--verbose",  "-v", action="store_true", default=False)

  return parser.parse_args()


# sample output :
# Dgemm v5.1.2
# clang version        : 16.0.0 (icx 2023.0.0.20221201)
# MKL version          : Intel(R) oneAPI Math Kernel Library Version 2023.0-Product Build 20221128 for Intel(R) 64 architecture applications
#  nb iteration : 0, performance cut : 0.000000, verify : 0
# 
# DGEMM_LWORK=19050496
# 
# The time/date of the run...  at Tue Oct 10 10:03:26 2023
# 
# This driver was compiled with:
#         -DITER=4 -DLINUX -DACCUR -DPREC=double
# Mapping of processors: Init -1, Exec -1
# Test run 30 seconds including 5 seconds rampup
# 
# Start of the loop...  at Tue Oct 10 10:03:26 2023
# 
# mesca5mod-63
#               lda    ldb    ldc
# (  1 of   1): NN   8000    120   8000 0 0 0
# 
# CPU-Node  GFlops  EcartType  #val  #Iter     %CPU  Elapse
#   0 - 1 : 2310.058     60.521   3760    5205  11186.21%   35.00
# 
# Sum Node  GFlops   EcartType  #val   #Iter      %CPU  Elapse    Overall
#       1 : 2310.058     60.521   3760    5205 11186.20%   35.00   2283.939
# 
# End of the run...  at Tue Oct 10 10:04:01 2023
# 
# Number of errors found=0 Total Error detected=0 mesca5mod-63
# 
# Performance counter stats for 'system wide':
#
#                                            link             Outgoing Data(GB) Outgoing Non-Data(GB)
#UPI Link 0 on Socket 0 -> UPI Link 1 on Socket 1                  158                    101
#UPI Link 0 on Socket 1 -> UPI Link 1 on Socket 0                  156                    113
#UPI Link 1 on Socket 0 -> UPI Link 0 on Socket 1                  158                    101
#UPI Link 1 on Socket 1 -> UPI Link 0 on Socket 0                  156                    113
#UPI Link 2 on Socket 0 -> UPI Link 2 on Socket 1                  158                    101
#UPI Link 2 on Socket 1 -> UPI Link 2 on Socket 0                  156                    113
#UPI Link 3 on Socket 0 -> UPI Link 3 on Socket 1                  158                    101
#UPI Link 3 on Socket 1 -> UPI Link 3 on Socket 0                  156                    113
#
#      10.543947599 seconds time elapsed
#
#    1101.036635000 seconds user
#      20.009375000 seconds sys

args=init()
blacklist=set()
port_blacklist=set()
# process the down ports into blacklist ( a list of strings in the format "s1-u:s2-u" where s1<s2)
if args.down_ports is not None:
  if "," in args.down_ports:
    ports=args.down_ports.split(",")
  else:
    ports= [ args.down_ports ]  
  try:  
    for port in ports:
      s,u=[ int(d) for d in port.split('-') ] 
      # special case : socket does not exist 
      if s>=args.sockets or s<0: continue
      # special case : upi port does not exist
      if u>=args.upis or u<0: continue
      # general case : store it
      port_blacklist.add( port )
  except:
    sys.stderr.write("error : the --down-ports format is s-u,s-u,...\n" )  
    sys.exit(1)


# process the down links into "blacklist" ( a list of strings in the format "s1-u:s2-u" where s1<s2)
if args.down_links is not None:
  if "," in args.down_links:
    couples=args.down_links.split(",")
  else:
    couples= [ args.down_links ]  
  try:  
    for couple in couples:
      linkA,linkB=couple.split(":")
      s0,u0= [ int(d) for d in linkA.split("-") ]
      s1,u1= [ int(d) for d in linkB.split("-") ]
      # special case : socket does not exist 
      if s0>=args.sockets or s0<0: continue
      if s1>=args.sockets or s1<0: continue
      # special case : upi port does not exist
      if u0>=args.upis or u0<0: continue
      if u1>=args.upis or u1<0: continue
      # force s0 to be less than s1 to ensure unicity
      if s0 > s1 :
          blacklist.add( "{}-{}:{}-{}".format(s1, u1, s0, u0) )
      else:  
        blacklist.add( couple )
  except:
    sys.stderr.write("error : the --down-links format is s-u:s-u,s-u:s-u,...\n" )  
    sys.exit(1)

if debug: print(blacklist)

# special case : all the upi links have been blacklisted
if 2*len(blacklist) >= args.sockets*args.upis:
  #the test is useless, and assumed true
  sys.exit(0)

looking4Gflop=True
looking4UPI=True
passedHeader=False
gflops="0"
dico={}
elapsed=10
datas=[]
nondatas=[]

for dataline in sys.stdin:
  cleaned=dataline.strip("\n ")  
  if len(cleaned) == 0: continue

  if looking4Gflop:
    if cleaned[:8]=="CPU-Node" and passedHeader==False:
      passedHeader=True
      continue
    if passedHeader:
      if cleaned[:5]=="0 - 1":
        fields=cleaned.split()
        gflops=fields[4]
        looking4Gflop=False
        passedHeader=False
        continue
  elif looking4UPI:
    fields=cleaned.split()
    if cleaned[:8]=="UPI Link":
      fromUPI=fields[2]
      fromSocket=fields[5]
      # ignore data if port has been switched off
      if fromSocket+"-"+fromUPI in port_blacklist: continue

      toUPI=fields[9]
      toSocket=fields[12]
      # ignore data if port has been switched off
      if toSocket+"-"+toUPI in port_blacklist: continue

      # special case : ignore data if this link has been black listed by user
      s0,u0=fromSocket,fromUPI
      s1,u1=toSocket,toUPI
      if int(s0)>int(s1):
        key=s1+'-'+u1+':'+s0+'-'+u0
      else:
        key=s0+'-'+u0+':'+s1+'-'+u1
      if key in blacklist:
        continue  
      # general case: process data line
      data=int(fields[13])
      nondata=int(fields[14])
      key="die_{},upi_{},die_{},upi_{}".format(fromSocket,fromUPI,toSocket,toUPI)
      dico[key]=(data,nondata)
      datas.append(data)
      nondatas.append(nondata)
    elif fields[2]=="time" and fields[3]=="elapsed":  
      elapsed=float(fields[0])  
      break


datas=[ x/elapsed for x in datas ]
nondatas=[ x/elapsed for x in nondatas ]

datamean=statistics.mean(datas)
nondatamean=statistics.mean(nondatas)

datavariance=statistics.variance(datas)
nondatavariance=statistics.variance(nondatas)

if args.verbose:
    print( "average outgoing data     : {0:4.1f}GB/s (variance={2:5.4f})\naverage outgoing non data : {1:4.1f}GB/s (variance={3:5.4f})".format(datamean, nondatamean, datavariance, nondatavariance) )
    for k,v in dico.items():
        print(k+" = "+"{0:5.2f}GB/s / {1:5.2f}GB/s".format(v[0]/elapsed, v[1]/elapsed))  

#checking if everything looks ok

# checking the number of links. It's a bit more complex , commenting out for the moment
#nlinks= args.sockets * args.upis - 2*len(blacklist)  # each blacklisted link counts twice, of course
#if len(datas)!=nlinks:
#    sys.stderr.write("Invalid number of UPI links : found {}, expecting {}\n".format(len(datas),nlinks))
#    sys.exit(1)
if datavariance>0.05:
    sys.stderr.write("Uneven data bandwidth between UPI links\n")
    sys.exit(1)
if datamean<.9*16:
    sys.stderr.write("Overall data bandwidth is low : found {0:5.2f}, expecting 90% of 16GB/s\n".format(datamean) )
    sys.exit(1)

sys.exit(0)

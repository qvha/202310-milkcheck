#!/usr/bin/python3
import re
import sys
import subprocess

commande=[ "/usr/local/BenchElem/x86_64/mlc", "--latency_matrix", "-b10000" ]
p=subprocess.Popen( commande, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, universal_newlines=True )
# sample output :  
# Intel(R) Memory Latency Checker - v3.10
# Command line parameters: --latency_matrix -b100000
# 
# Using buffer size of 97.656MiB
# Measuring idle latencies for sequential access (in ns)...
#                 Numa node
# Numa node            0       1
#        0         117.2   201.9
#        1         200.7   115.0

motif=re.compile("[ ]+([0-9]+) [0-9 ]+")

for dataline in p.stdout:
  cleaned=dataline.strip("\n ")  
  if len(cleaned) == 0: continue
  fields=cleaned.split()

  try:
    index=int(fields[0])
  except:
    continue  
 
  if index==0:
    [ print(i.split(".")[0]) for i in fields[1:] ]
    break


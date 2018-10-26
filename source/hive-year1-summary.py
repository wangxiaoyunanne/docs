#!/usr/bin/env python3

# run as
# ./hive-year1-summary.py && open darpa.pdf

import os
import tempfile
import subprocess
from pandocfilters import toJSONFilter, Str

files = sorted([f for f in os.listdir('.')
                if ((f.startswith('hive_') and
                     f.endswith('.html.md') and
                     f != 'hive_year1_summary.html.md' and
                     f != 'hive_template.html.md' and
                     f != 'hive_scaling.html.md'))])
files.insert(0, 'hive_year1_summary.html.md')
# files += 'hive_scaling.html.md'

# for f in files:
#     with open(f) as in_md:
#         print(in_md.read())

pandoc_cmd = ['pandoc',
              '--template=darpa-template.tex',
              '--variable', 'title=A Commodity Performance Baseline for HIVE Graph Applications:\\\\Year 1 Report',
              '--variable', 'author=Ben Johnson \\and Weitang Liu \\and Agnieszka Łupińska \\and Muhammad Osama \\and John D. Owens \\and Yuechao Pan \\and Leyuan Wang \\and Xiaoyun Wang \\and Carl Yang',
              '--variable', 'postauthor=UC Davis',
              '--variable', 'documentclass=memoir',
              '--variable', 'fontsize=10pt',
              '--variable', 'classoption=oneside',
              # '--variable', 'classoption=article',
              '--variable', 'toc-depth=0',
              '--toc',
              '-o', 'darpa.pdf',
              # '-o', 'darpa.tex',
              ]
pandoc_cmd.extend(files)

print(pandoc_cmd)

subprocess.run(pandoc_cmd)

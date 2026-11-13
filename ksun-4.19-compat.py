#!/usr/bin/env python3
"""4.19 compat for KernelSU-Next dev-susfs file_wrapper.c.

file_operations.iopoll and remap_file_range (and REMAP_FILE_DEDUP) were
added after 4.19; the wrapper only forwards them to the original fops, so
compiling them out on older trees costs nothing.
"""
import re
import sys

p = sys.argv[1]
s = open(p).read()

if "#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 4, 0)\n#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 1, 0)\nstatic int ksu_wrapper_iopoll" in s:
    print("already patched")
    sys.exit(0)

pat = re.compile(r'(#if LINUX_VERSION_CODE >= KERNEL_VERSION\(6, 1, 0\)\n'
                 r'static int ksu_wrapper_iopoll.*?'
                 r'return orig->f_op->iopoll\(kiocb, spin\);\n\}\n#endif\n)', re.S)
assert len(pat.findall(s)) == 1, "iopoll block not found"
s = pat.sub(r'#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 4, 0)\n\1#endif\n', s)

pat = re.compile(r'(static loff_t ksu_wrapper_remap_file_range\(.*?\n\}\n)', re.S)
assert len(pat.findall(s)) == 1, "remap block not found"
s = pat.sub(r'#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 4, 0)\n\1#endif\n', s)

a = "    p->ops.iopoll = fp->f_op->iopoll ? ksu_wrapper_iopoll : NULL;\n"
assert s.count(a) == 1, "iopoll assignment not found"
s = s.replace(a, "#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 4, 0)\n" + a + "#endif\n")

b = ("    p->ops.remap_file_range =\n"
     "        fp->f_op->remap_file_range ? ksu_wrapper_remap_file_range : NULL;\n")
assert s.count(b) == 1, "remap assignment not found"
s = s.replace(b, "#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 4, 0)\n" + b + "#endif\n")

open(p, "w").write(s)
print("patched", p)

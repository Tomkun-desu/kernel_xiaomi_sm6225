#!/usr/bin/env python3
"""4.19 compat for KernelSU-Next dev-susfs (tree root is argv[1]).

file_wrapper.c: iopoll/remap_file_range/REMAP_FILE_DEDUP arrived after 4.19;
the wrapper only forwards them, so compiling them out costs nothing.
seccomp_cache.c: 4.19 has no per-arch seccomp cache (struct action_cache);
the allow/clear hooks are unused, so stub them.
"""
import os
import re
import sys

root = sys.argv[1]


def file_wrapper():
    p = os.path.join(root, "kernel/infra/file_wrapper.c")
    s = open(p).read()
    if "#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 4, 0)\n#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 1, 0)\nstatic int ksu_wrapper_iopoll" in s:
        print("file_wrapper: already patched")
        return

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
    print("file_wrapper: patched")


def seccomp_cache():
    p = os.path.join(root, "kernel/infra/seccomp_cache.c")
    s = open(p).read()
    if "#if LINUX_VERSION_CODE < KERNEL_VERSION(5, 0, 0)" in s:
        print("seccomp_cache: already patched")
        return
    anchor = "#include <linux/version.h>\n"
    assert s.count(anchor) == 1, "version.h include not found"
    stub = (anchor
            + "#include <linux/seccomp.h>\n"
            + "#if LINUX_VERSION_CODE < KERNEL_VERSION(5, 0, 0)\n"
            + "void ksu_seccomp_clear_cache(struct seccomp_filter *filter, int nr) {}\n"
            + "void ksu_seccomp_allow_cache(struct seccomp_filter *filter, int nr) {}\n"
            + "#else\n")
    s = s.replace(anchor, stub, 1).rstrip("\n") + "\n#endif\n"
    open(p, "w").write(s)
    print("seccomp_cache: patched")


file_wrapper()
seccomp_cache()

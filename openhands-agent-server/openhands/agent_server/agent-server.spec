# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for OpenHands Agent Server with PEP 420 (implicit namespace) layout.
"""

from pathlib import Path
import os
import site
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    copy_metadata,
)

# Get the project root directory (current working directory when running PyInstaller)
project_root = Path.cwd()
# Namespace roots must be in pathex so PyInstaller can find 'openhands/...'
PATHEX = [
    project_root / "openhands-agent-server",
    project_root / "openhands-sdk",
    project_root / "openhands-tools",
    project_root / "openhands-workspace",
]

# Entry script for the agent server package (namespace: openhands/agent_server/__main__.py)
ENTRY = str(project_root / "openhands-agent-server" / "openhands" / "agent_server" / "__main__.py")

# Find fakeredis package location to get commands.json with correct path
def get_fakeredis_data():
    """Get fakeredis data files with correct directory structure.
    
    fakeredis/model/_command_info.py uses Path(__file__).parent.parent / "commands.json"
    which means it expects commands.json to be at fakeredis/commands.json when accessed
    from fakeredis/model/. We need to ensure the model/ subdirectory exists in the bundle.
    """
    import fakeredis
    fakeredis_dir = Path(fakeredis.__file__).parent
    commands_json = fakeredis_dir / "commands.json"
    
    data_files = []
    if commands_json.exists():
        # Add commands.json to fakeredis/ directory
        data_files.append((str(commands_json), "fakeredis"))
    
    # Add a placeholder file to create the model/ subdirectory structure
    # This ensures Path(__file__).parent.parent works correctly for model/ modules
    model_dir = fakeredis_dir / "model"
    if model_dir.exists():
        # Find any .py file in model/ to include (PyInstaller needs at least one file)
        for py_file in model_dir.glob("*.py"):
            # We don't actually need the .py files (they're compiled), but we need
            # the __init__.py to create the directory structure
            if py_file.name == "__init__.py":
                data_files.append((str(py_file), "fakeredis/model"))
                break
    
    return data_files

a = Analysis(
    [ENTRY],
    pathex=PATHEX,
    binaries=[],
    datas=[
        # Third-party packages that ship data
        *collect_data_files("tiktoken"),
        *collect_data_files("tiktoken_ext"),
        *collect_data_files("litellm"),
        *collect_data_files("fastmcp"),
        *collect_data_files("mcp"),
        *collect_data_files("fakeredis"),  # Required for commands.json used by fakeredis ACL
        *get_fakeredis_data(),  # Ensure fakeredis/model/ directory structure exists

        # OpenHands SDK prompt templates (adjusted for shallow namespace layout)
        *collect_data_files("openhands.sdk.agent", includes=["prompts/*.j2"]),
        *collect_data_files("openhands.sdk.context.condenser", includes=["prompts/*.j2"]),
        *collect_data_files("openhands.sdk.context.prompts", includes=["templates/*.j2"]),

        # OpenHands Tools templates
        *collect_data_files("openhands.tools.delegate", includes=["templates/*.j2"]),

        # OpenHands Tools browser recording JS files
        *collect_data_files("openhands.tools.browser_use", includes=["js/*.js"]),

        # Package metadata for importlib.metadata
        *copy_metadata("fastmcp"),
        *copy_metadata("litellm"),
    ],
    hiddenimports=[
        # Pull all OpenHands modules from the namespace (PEP 420 safe once pathex is correct)
        *collect_submodules("openhands.sdk"),
        *collect_submodules("openhands.tools"),
        *collect_submodules("openhands.workspace"),
        *collect_submodules("openhands.agent_server"),

        # Third-party dynamic imports
        *collect_submodules("tiktoken"),
        *collect_submodules("tiktoken_ext"),
        *collect_submodules("litellm"),
        *collect_submodules("fastmcp"),
        *collect_submodules("fakeredis"),
        *collect_submodules("lupa"),  # Required for fakeredis[lua] Lua scripting support

        # mcp subpackages used at runtime (avoid CLI)
        "mcp.types",
        "mcp.client",
        "mcp.server",
        "mcp.shared",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim size
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "IPython",
        "jupyter",
        "notebook",
        # Exclude mcp CLI parts that pull in typer/extra deps
        "mcp.cli",
        "mcp.cli.cli",
    ],
    noarchive=False,
    # IMPORTANT: don't use optimize=2 (-OO); it strips docstrings needed by parsers (e.g., PLY/bashlex)
    optimize=0,
)

# Remove problematic system libraries that should use host versions
# This prevents bundling incompatible libgcc_s.so.1 that lacks GCC_14.0 symbols
a.binaries = [x for x in a.binaries if not x[0].startswith('libgcc_s.so')]

# ---------------------------------------------------------------------------
# Fix executable stack flags on bundled shared libraries.
#
# CPython's libpython3.13.so.1.0 (as distributed by astral-sh/uv) is built
# with PT_GNU_STACK RWX (requests executable stack).  glibc >= 2.41-12+deb13u2
# (Debian Trixie, used in the nikolaik runtime image) tightened NX-stack
# enforcement and the dynamic linker now rejects such libraries with EINVAL.
# sysbox-runc's seccomp policy also blocks the mprotect(PROT_EXEC) fallback.
#
# We clear the PF_X (executable) bit from PT_GNU_STACK on every bundled .so
# *before* PyInstaller's strip + bundle step so the onefile archive contains
# clean libraries that load under strict NX policies.
# ---------------------------------------------------------------------------
import struct
import shutil
import tempfile

def _clear_execstack(filepath):
    """Clear PF_X from PT_GNU_STACK in a 64-bit ELF. Returns True if patched."""
    with open(filepath, 'r+b') as f:
        if f.read(4) != b'\x7fELF':
            return False
        ei_class = f.read(1)[0]
        if ei_class != 2:  # 64-bit only
            return False
        f.seek(32)
        e_phoff = struct.unpack('<Q', f.read(8))[0]
        f.seek(54)
        e_phentsize, e_phnum = struct.unpack('<HH', f.read(4))
        for i in range(e_phnum):
            off = e_phoff + i * e_phentsize
            f.seek(off)
            p_type = struct.unpack('<I', f.read(4))[0]
            if p_type == 0x6474e551:  # PT_GNU_STACK
                p_flags = struct.unpack('<I', f.read(4))[0]
                if p_flags & 0x1:  # PF_X (executable)
                    f.seek(off + 4)
                    f.write(struct.pack('<I', p_flags & ~0x1))
                    return True
                return False
    return False

_nxfix_tmpdir = tempfile.mkdtemp(prefix='pyinstaller_nxfix_')
_fixed_binaries = []
for name, path, typecode in a.binaries:
    if '.so' in name:
        tmp_path = os.path.join(_nxfix_tmpdir, name.replace(os.sep, '_'))
        shutil.copy2(path, tmp_path)
        if _clear_execstack(tmp_path):
            print(f'  [NX-fix] Cleared executable stack: {name}')
            _fixed_binaries.append((name, tmp_path, typecode))
            continue
        os.unlink(tmp_path)
    _fixed_binaries.append((name, path, typecode))
a.binaries = _fixed_binaries

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="openhands-agent-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

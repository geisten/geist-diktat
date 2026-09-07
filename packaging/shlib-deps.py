#!/usr/bin/env python3
"""Ask dpkg for the ABI-versioned dependencies of the actual ELF binaries."""
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory(prefix='geist-shlibs-') as temp:
    temp=Path(temp);(temp/'debian').mkdir()
    (temp/'debian/control').write_text('Source: geist-diktat\nSection: sound\nPriority: optional\nMaintainer: germar <g.schlegel@geisten.net>\n\nPackage: geist-diktat\nArchitecture: any\nDescription: local dictation\n')
    output=subprocess.check_output(['dpkg-shlibdeps','-O',*['-e'+str(Path(p).resolve()) for p in sys.argv[1:]]],cwd=temp,text=True)
    dependency=next(line.partition('=')[2] for line in output.splitlines() if line.startswith('shlibs:Depends='))
    if not dependency:raise ValueError('missing shared-library dependency evidence')
    print(dependency)

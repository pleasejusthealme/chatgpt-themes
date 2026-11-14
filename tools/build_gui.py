"""Compile the source-only native patcher; does not bundle ChatGPT or Python."""
import argparse
from pathlib import Path
import plistlib
import shutil
import subprocess

ROOT=Path(__file__).resolve().parent.parent

def run(*args):
    subprocess.run(args,check=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'dist/ChatGPT Themes Patcher.app')
    args=p.parse_args();app=args.output.resolve()
    if app.exists():raise SystemExit('Output already exists; choose a new path')
    binary=app/'Contents/MacOS/ChatGPTThemesPatcher'
    resources=app/'Contents/Resources/project'
    binary.parent.mkdir(parents=True);resources.mkdir(parents=True)
    for directory in ['manager','tools']:
        shutil.copytree(ROOT/directory,resources/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copyfile(ROOT/'LICENSE',resources/'LICENSE')
    shutil.copyfile(ROOT/'README.md',resources/'README.md')
    (app/'Contents/Info.plist').write_bytes(plistlib.dumps({
        'CFBundleIdentifier':'local.chatgptthemes.patcher',
        'CFBundleName':'ChatGPT Themes Patcher','CFBundleDisplayName':'ChatGPT Themes Patcher',
        'CFBundleExecutable':'ChatGPTThemesPatcher','CFBundlePackageType':'APPL',
        'CFBundleShortVersionString':'0.2.0','CFBundleVersion':'2',
        'LSMinimumSystemVersion':'13.0','NSHighResolutionCapable':True,
        'NSHumanReadableCopyright':'ChatGPT Themes contributors. MIT License.'}))
    run('/usr/bin/xcrun','clang','-fobjc-arc','-fblocks','-fno-modules',
        '-mmacosx-version-min=13.0','-O2','-framework','Cocoa',
        str(ROOT/'app/Patcher.m'),'-o',str(binary))
    run('/usr/bin/codesign','--force','--sign','-',str(app))
    run('/usr/bin/codesign','--verify','--strict',str(app))
    run(str(binary),'--self-test')
    print('Built:',app)
    print('Python 3 is required on the destination Mac. No ChatGPT binaries are included.')

if __name__=='__main__':main()

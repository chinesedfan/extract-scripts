#!/bin/sh
set -e

mkdir -p decompiler
cd decompiler
git clone https://github.com/icsharpcode/ILSpy.git
cd ILSpy/ICSharpCode.Decompiler
# xbuild provided by mono
xbuild ICSharpCode.Decompiler.csproj
cp -rt ../.. bin/Debug/*.dll
cd ../..
dmcs -out:decompile.exe ../decompile.cs \
	-r:Mono.Cecil.dll \
	-r:ICSharpCode.Decompiler.dll \
	-r:ICSharpCode.NRefactory.dll \
	-r:ICSharpCode.NRefactory.CSharp.dll
mono decompile.exe some/Assembly-CSharp.dll some/project-dir

#!/bin/sh
set -e

mkdir -p "build/decompiler/"
xbuild /property:OutputPath="build/decompiler/" ILSpy/ICSharpCode.Decompiler/ICSharpCode.Decompiler.csproj
exit
dmcs -out:build/decompile.exe ../decompile.cs \
	-r:Mono.Cecil.dll \
	-r:ICSharpCode.Decompiler.dll \
	-r:ICSharpCode.NRefactory.dll \
	-r:ICSharpCode.NRefactory.CSharp.dll
mono decompile.exe some/Assembly-CSharp.dll some/project-dir

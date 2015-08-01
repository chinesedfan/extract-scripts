#!/bin/bash

BASEDIR="$(realpath $(dirname $0))"
GITDIR="$BASEDIR/hs-data.git"

git init "$GITDIR"
cp "$BASEDIR/README-hs-data.md" "$GITDIR/README.md"
git -C "$GITDIR" remote add origin git@github.com:HearthSim/hs-data.git
git -C "$GITDIR" add README.md
git -C "$GITDIR" commit -m "Initial commit"

patches=(
	["3140"]="1.0.0"
	["3388"]="1.0.0"
	["3664"]="1.0.0"
	["3749"]="1.0.0"
	["3890"]="1.0.0"
	["3937"]="1.0.0"
	["4217"]="1.0.0"
	["4243"]="1.0.0"
	["4458"]="1.0.0"
	["4482"]="1.0.0"
	["4944"]="1.0.0"
	["4973"]="1.0.0"
	["5170"]="1.0.0"
	["5314"]="1.0.0"
	["5435"]="1.0.0"
	["5506"]="1.0.0"
	["5834"]="1.0.0"
	["6024"]="1.1.0"
	["6141"]="1.1.0"
	["6187"]="1.1.0"
	["6284"]="1.1.0"
	["6485"]="1.2.0"
	["6898"]="1.3.0"
	["7234"]="2.0.0"
	["7628"]="2.1.0"
	["7785"]="2.1.0"
	["7835"]="2.2.0"
	["8036"]="2.2.0"
	["8108"]="2.3.0"
	["8311"]="2.4.0"
	["8416"]="2.5.0"
	["8834"]="2.6.0"
	["9166"]="2.7.0"
	["9554"]="2.8.0"
)

cd "$BASEDIR/out"
for build in *; do
	patch="${patches[$build]}"
	echo "Committing files for $build"
	dir="$BASEDIR/out/$build"
	rm -rf "$GITDIR/DBF"
	cp -rf "$dir"/* "$GITDIR"
	sed -i "s/Version: .*/Version: $patch.$build/" "$GITDIR/README.md"
	git -C "$GITDIR" add "$GITDIR/DBF"
	git -C "$GITDIR" add "$GITDIR/CardDefs.xml"
	git -C "$GITDIR" commit -am "Update to patch $patch.$build"
	git -C "$GITDIR" tag -am "Patch $patch.$build" $build
done

git -C "$GITDIR" push --set-upstream -f origin master
git -C "$GITDIR" push --tags -f

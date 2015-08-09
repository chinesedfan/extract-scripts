#!/bin/bash
BASEDIR="$(readlink -f $(dirname $0))"
PROCESSED_DIR="$BASEDIR/build/processed"
DECOMPILED_DIR="$BASEDIR/build/decompiled"

export GIT_AUTHOR_NAME="HearthSim Bot"
export GIT_AUTHOR_EMAIL="commits@hearthsim.info"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"

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


HSDATA_GIT="$BASEDIR/hs-data.git"
HSDATA_REMOTE="git@github.com:HearthSim/hs-data.git"

git init "$HSDATA_GIT"
cp "$BASEDIR/README-hs-data.md" "$HSDATA_GIT/README.md"
git -C "$HSDATA_GIT" remote add origin "$HSDATA_REMOTE"
git -C "$HSDATA_GIT" add README.md
git -C "$HSDATA_GIT" commit -m "Initial commit"

for dir in "$PROCESSED_DIR"/*; do
	build=$(basename "$dir")
	patch="${patches[$build]}"
	echo "Committing files for $build"
	rm -rf "$HSDATA_GIT/DBF"
	cp -rf "$dir"/* "$HSDATA_GIT"
	sed -i "s/Version: .*/Version: $patch.$build/" "$HSDATA_GIT/README.md"
	git -C "$HSDATA_GIT" add "$HSDATA_GIT/DBF"
	git -C "$HSDATA_GIT" add "$HSDATA_GIT/CardDefs.xml"
	git -C "$HSDATA_GIT" commit -am "Update to patch $patch.$build"
	git -C "$HSDATA_GIT" tag -am "Patch $patch.$build" $build
done

git -C "$HSDATA_GIT" push --set-upstream -f origin master
git -C "$HSDATA_GIT" push --tags -f

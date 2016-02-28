#!/bin/bash
BASEDIR="$(readlink -f $(dirname $0))"
BUILDDIR="$BASEDIR/build"
GH="git@github.com"

export GIT_AUTHOR_NAME="HearthSim Bot"
export GIT_AUTHOR_EMAIL="commits@hearthsim.info"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"

patches=(
	["3140"]="1.0.0 2013-06-05"
	["3388"]="1.0.0 2013-06-22"
	["3604"]="1.0.0 2013-08-12"
	["3645"]="1.0.0 2013-08-13"
	["3664"]="1.0.0 2013-08-14"
	["3749"]="1.0.0 2013-08-30"
	["3890"]="1.0.0 2013-10-02"
	["3937"]="1.0.0 2013-10-17"
	["4217"]="1.0.0 2013-12-10"
	["4243"]="1.0.0 2013-12-18"
	["4442"]="1.0.0 2013-01-13"
	["4458"]="1.0.0 2014-01-16"
	["4482"]="1.0.0 2014-01-17"
	["4944"]="1.0.0 2014-03-11"
	["4973"]="1.0.0 2014-03-13"
	["5170"]="1.0.0 2014-04-10"
	["5314"]="1.0.0 2014-05-08"
	["5435"]="1.0.0 2014-05-21"
	["5506"]="1.0.0 2014-05-28"
	["5834"]="1.0.0 2014-06-30"
	["6024"]="1.1.0 2014-07-22"
	["6141"]="1.1.0 2014-07-31"
	["6187"]="1.1.0 2014-08-06"
	["6284"]="1.1.0 2014-08-16"
	["6485"]="1.2.0 2014-09-22"
	["6898"]="1.3.0 2014-10-29"
	["7234"]="2.0.0 2014-12-04"
	["7628"]="2.1.0 2015-01-29"
	["7785"]="2.1.0 2015-02-09"
	["7835"]="2.2.0 2015-02-25"
	["8036"]="2.2.0 2015-02-26"
	["8108"]="2.3.0 2015-03-19"
	["8311"]="2.4.0 2015-03-31"
	["8416"]="2.5.0 2015-04-14"
	["8834"]="2.6.0 2015-05-14"
	["9166"]="2.7.0 2015-06-15"
	["9554"]="2.8.0 2015-06-29"
	["9786"]="3.0.0 2015-08-18"
	["10357"]="3.1.0 2015-09-29"
	["10604"]="3.2.0 2015-10-20"
	["10784"]="4.0.0 2015-11-10"
	["10833"]="4.0.0 2015-11-10"
	["10956"]="4.1.0 2015-12-04"
	["11461"]="4.1.0 2016-02-10"
)

declare -A directories=(
	["hscode"]="$BUILDDIR/decompiled"
	["hsdata"]="$BUILDDIR/processed"
	["hsproto"]="$BUILDDIR/protos"
)

declare -A remotes=(
	["hscode"]="$GH:shadowhugs/hs-code.git"
	["hsdata"]="$GH:HearthSim/hs-data.git"
	["hsproto"]="$GH:HearthSim/hs-proto.git"
)


function _init-repo() {
	PROJECT="$1"
	REPO="$BASEDIR/$PROJECT.git"
	GIT="git -C $REPO"
	README="$BASEDIR/README-$PROJECT.md"
	REMOTE="${remotes[$PROJECT]}"

	echo "Initializing $PROJECT"
	rm -rf "$REPO"
	git init "$REPO"
	cp "$README" "$REPO/README.md"
	$GIT remote add origin "$REMOTE"
	$GIT add README.md
	$GIT commit -m "Initial commit"
}

function _commit() {
	PROJECT=$1
	BUILD=$2
	REPO="$BASEDIR/$PROJECT.git"
	GIT="git -C $REPO"
	patch=$(printf "${patches[$BUILD]}" | cut -f1 -d " ")
	date="$(printf "${patches[$BUILD]}" | cut -f2 -d " ") 12:00:00 +0000"
	dir="${directories[$PROJECT]}/$BUILD"
	export GIT_AUTHOR_DATE="$date"

	[[ -d "$dir" ]] || continue
	echo "Committing $PROJECT for $patch.$BUILD"

	sed -i "s/Version: .*/Version: $patch.$BUILD/" "$REPO/README.md"
	_update-$PROJECT

	$GIT add "$REPO" &>/dev/null
	$GIT commit -am "Update to patch $patch.$BUILD" &>/dev/null
	$GIT tag -am "Patch $patch.$BUILD" $BUILD
}

function _push() {
	PROJECT=$1
	REPO="$BASEDIR/$PROJECT.git"
	git -C "$REPO" push --set-upstream --follow-tags -f origin master
}

function _update-hsdata() {
	manifest="$BUILDDIR/extracted/$BUILD/manifest-cards.csv"
	playerrors="$BUILDDIR/extracted/$BUILD/Data/PlayErrors.xml"
	[[ -s "$manifest" ]] && cp "$manifest" "$REPO"
	[[ -s "$playerrors" ]] && cp "$playerrors" "$REPO"
	rm -rf "$REPO/DBF"
	cp -rf "$dir"/* "$REPO"
}

function _update-hscode() {
	rm -rf "$REPO"/**/*.cs
	cp -rf "$dir"/* "$REPO"
}

function _update-hsproto() {
	rm -rf "$REPO/bnet" "$REPO/pegasus"
	cp -rf "$dir"/* "$REPO"
}


_init-repo "hsdata"

for BUILD in "${!patches[@]}"; do
	_commit hsdata $BUILD
done


_init-repo "hscode"

for BUILD in "${!patches[@]}"; do
	_commit hscode $BUILD
done


_init-repo "hsproto"

for BUILD in "${!patches[@]}"; do
	_commit hsproto $BUILD
done


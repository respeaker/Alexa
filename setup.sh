

CURRENT_DIR="$( pwd )"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd $SCRIPT_DIR

if [ ! -d respeaker ]; then
    echo 'not found respeaker python library, get it from https://github.com/respeaker/respeaker_python_library'
    git clone https://github.com/respeaker/respeaker_python_library.git
    mv respeaker_python_library/respeaker respeaker

    echo 'Install required python packages'
    pip install -r requirements.txt
fi

cd $CURRENT_DIR



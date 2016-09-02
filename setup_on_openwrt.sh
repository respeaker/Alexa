
if [ ! -d respeaker ]; then
    echo 'not found respeaker python library, get it from https://github.com/respeaker/respeaker_python_library'
    git clone https://github.com/respeaker/respeaker_python_library.git
    mv respeaker_python_library/respeaker respeaker

    echo 'Install CherryPy and Requests'
    pip install CherryPy requests
fi






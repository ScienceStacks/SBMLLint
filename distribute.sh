# Builds source and updates PyPI
echo "Have you updated the person number? Press enter to continue."
read -p "$*"
rm -rf dist
python setup.py sdist
twine upload dist/*

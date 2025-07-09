echo "--- Packaging Lambda function ---"
PACKAGE_DIR="../python/package"
ZIP_FILE="../python/StockAnalyzer.zip"

# Clean up previous package to ensure a fresh build
rm -rf $PACKAGE_DIR
rm -f $ZIP_FILE

# Create package directory and install dependencies from requirements.txt
mkdir -p $PACKAGE_DIR
pip install -r ../python/requirements.txt -t $PACKAGE_DIR --quiet

# Copy your source code into the package
cp ../python/StockAnalyzer.py $PACKAGE_DIR/

# Create the zip file from within the package directory
cd $PACKAGE_DIR && zip -r $ZIP_FILE . -q
echo "--- Packaging complete ---"
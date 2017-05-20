mkdir dist
pip install -r requirements.txt -t ./dist
cp service.py dist/service.py
cd dist
zip -r ../deploy.zip *
cd ..
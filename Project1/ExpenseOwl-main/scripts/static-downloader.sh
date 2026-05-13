#!/bin/bash

echo "downloading chart.js minified script"
curl -sL https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js -o internal/web/templates/chart.min.js
echo "downloading font awesome minified CSS"
curl -sL https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css -o internal/web/templates/fa.min.css

echo "downloading font awesome webfonts"
mkdir -p temp_webfonts
cd temp_webfonts
curl -sL https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/webfonts/fa-brands-400.woff2 -O
curl -sL https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/webfonts/fa-regular-400.woff2 -O
curl -sL https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/webfonts/fa-solid-900.woff2 -O
curl -sL https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/webfonts/fa-v4compatibility.woff2 -O
mv *.woff2 ../internal/web/templates/webfonts/
cd ..
rmdir temp_webfonts

# change reference of cdn webfonts to local webfonts in css
sed -i.bak 's|https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/webfonts/|/webfonts/|g' internal/web/templates/fa.min.css
rm internal/web/templates/fa.min.css.bak

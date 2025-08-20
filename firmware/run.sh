cd suno-api &&
npm i &&
npm run dev &

cd ../ &&
source env/bin/activate &&
python main.py &
cd ../ &&

echo "Suno API is running on http://localhost:3000"
echo "Jukebox firmware is running"

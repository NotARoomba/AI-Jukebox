cd suno-api &
npm i &
npm run dev &
echo "Suno API is running on http://localhost:3000"

cd ../

source env/bin/activate
python main.py &
echo "Jukebox firmware is running"


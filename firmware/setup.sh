sudo apt install python3-dev python3-pip python3-venv

python -m venv env --system-site-packages
source env/bin/activate

python3 -m pip install spidev
python3 -m pip install mfrc522
python3 -m pip install requests
python3 -m pip install python-vlc

sudo apt install -y wget
pip3 install adafruit-python-shell
wget https://github.com/adafruit/Raspberry-Pi-Installer-Scripts/raw/main/i2samp.py
sudo -E env PATH=$PATH python3 i2samp.py

# Edit sudo nano /etc/modprobe.d/raspi-blacklist.conf
# Comment all lines that contain

#blacklist i2c-bcm2708
#blacklist snd-soc-pcm512x
#blacklist snd-soc-wm8804

# Add the following lines to /etc/asound.conf
echo "pcm.speakerbonnet {
   type hw card 0
}

pcm.dmixer {
   type dmix
   ipc_key 1024
   ipc_perm 0666
   slave {
     pcm "speakerbonnet"
     period_time 0
     period_size 1024
     buffer_size 8192
     rate 44100
     channels 2
   }
}

ctl.dmixer {
    type hw card 0
}

pcm.softvol {
    type softvol
    slave.pcm "dmixer"
    control.name "PCM"
    control.card 0
}

ctl.softvol {
    type hw card 0
}

pcm.!default {
    type             plug
    slave.pcm       "softvol"
}" > /etc/asound.conf

# Edit sudo nano /etc/modules
# Comment snd_bcm2835

# Then edit sudo nano /boot/firmware/config.txt
# Put # infront of dtparam=audio=on
# Add dtoverlay=max98357a


# Suno API Setup Script
git clone https://github.com/gcui-art/suno-api.git
cd suno-api
npm install

# Then test http://localhost:3000/api/get_limit
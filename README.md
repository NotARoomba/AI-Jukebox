<h1 align="center"> 
  <br>
  <img src="images/jukebox_logo.png" alt="Jukebox concept" width="200">
  <br>
  Jukebox 
</h1>

<h4 align="center">A Minecraft‑inspired AI‑powered music jukebox using NFC‑tagged disks!</h4>

<div align="center">

![Python](https://img.shields.io/badge/python-%233776AB.svg?style=for-the-badge&logo=python&logoColor=white)
![Fusion 360](https://img.shields.io/badge/fusion%20360-%23F78F1E.svg?style=for-the-badge&logo=autodesk&logoColor=white)
![KiCad](https://img.shields.io/badge/kicad-%2300578F.svg?style=for-the-badge&logo=kicad&logoColor=white)

</div>

<p align="center">
  <a href="#key-features">Key Features</a> •
  <a href="#components-and-costs">Components & Costs</a> •
  <a href="#case-and-cad">Case & CAD</a> •
  <a href="3pcb-and-wiring">PCB & Wiring</a> •
  <a href="#credits">Credits</a>
</p>

## 🔧 Key Features

- **NFC‑enabled Disks**: Tap‑to‑play AI‑generated tracks or album content.
- **Grouped Albums**: Use prompt‑encoding or album playback modes.
- **Satisfying Push‑Push Mechanics**: Disks elegantly eject on second push.
- **Custom Cube Frame**: 16 cm wooden case with 3D printed internals.
- **Audio Output**: Integrated speaker + MAX98357 amplifier, with Bluetooth support.
- **Raspberry Pi Zero 2 W** powers logic and audio playback.
- **PCB Wiring** for NFC and amp modules designed in KiCad.

## 🧩 Components & Costs

| Item                  | Price (COP)             | Price (USD) | Source                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| --------------------- | ----------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Raspberry Pi Zero 2 W | 78,018                  | 18.92       | [Aliexpress](https://es.aliexpress.com/item/1005007064834607.html?spm=a2g0o.productlist.main.6.599cOUgzOUgzBb&algo_pvid=c47c0628-1124-436d-8814-0892329938ac&algo_exp_id=c47c0628-1124-436d-8814-0892329938ac-5&pdp_ext_f=%7B%22order%22%3A%22600%22%2C%22eval%22%3A%221%22%7D&pdp_npi=4%40dis%21COP%2157654.82%2155533.60%21%21%2113.59%2113.09%21%402101c59117499136772585670e8cee%2112000039289377778%21sea%21CO%210%21ABX&curPageLogUid=9lbu4jPdgJ93&utparam-url=scene%3Asearch%7Cquery_from%3A) |
| Speaker Amp Max98357  | 22,140                  | 5.40        | [Online Marketplace](https://articulo.mercadolibre.com.co/MCO-2424374156-max98357-dac-convertidor-digital-analogico-amplificador-3w-_JM#polycard_client=search-nordic&position=12&search_layout=stack&type=item&tracking_id=20f32b76-e12d-44f0-9b37-b97e2951a224&wid=MCO2424374156&sid=search)                                                                                                                                                                                                       |
| NFC Tags              | 44,105                  | 10.70       | [Online Marketplace](https://www.mercadolibre.com.co/a-100-unidadeslote-para-telefonos-con-chip-ntag215-nfc-pvc/p/MCO2011890227#polycard_client=search-nordic&searchVariation=MCO2011890227&position=6&search_layout=grid&type=product&tracking_id=ad232278-3e0d-49d9-bf02-d20f7d0de3cb&wid=MCO2772795516&sid=search)                                                                                                                                                                                |
| RFID Kit RC522        | 12,500                  | 3.03        | [Online Marketplace](https://articulo.mercadolibre.com.co/MCO-592398205-kit-rfid-rc522-receptor-tarjeta-y-llavero-_JM#polycard_client=search-nordic&position=11&search_layout=stack&type=item&tracking_id=789bf9be-1bc4-40a3-bf0c-bac5863410f3&wid=MCO592398205&sid=search)                                                                                                                                                                                                                          |
| Push Push Mechanism   | 19,400 (already bought) | 4.71        | Local Hardware Store                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 1cm Blocks of Wood    | 33,760 (each, 2 units)  | 8.19        | [Temu](https://share.temu.com/08dAAkNGvvA)                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| **SubTotal**          | **272,750**             | **66.18**   |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| **Shipping Costs**    | **105,000**             | **25.00**   | Estimated                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| **Total**             | **377,750**             | **91.18**   |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

## 📐 Case & CAD

- Designed in Fusion 360 as a 16 cm cube.
- 3D printed internal supports, wooden outer shell, and speaker cut‑out.
- Push‑push hardware custom‑fitted into disk slot.

![alt text](/images/disk.png)

![alt text](/images/jukeboxdiskinside.png)

## 📝 PCB & Wiring

- Designed wiring in KiCad for Raspberry Pi ↔ RC522 NFC ↔ MAX98357 amp.
- Followed PiMyLifeUp tutorial for RC522, and Adafruit guide for MAX98357 wiring.

![alt text](/images/wiring.png)

## Credits

This project uses:

- [KiCad](https://www.kicad.org/)
- [Python](https://www.python.org/)
- [Fusion 360](https://www.autodesk.com/products/fusion-360/overview)
- [RC522 Tutorial](https://pimylifeup.com/raspberry-pi-rfid-rc522/)
- [I2S Amp Guide](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp/raspberry-pi-wiring)

## You may also like...

- [Tamaki](https://github.com/NotARoomba/Tamaki) – Tamagotchi macropad
- [NivelesDeNiveles](https://github.com/NotARoomba/NivelesDeNiveles) – Flood alert app
- [ROCKETMEN](https://github.com/NotARoomba/ROCKETMEN) – Flight controller files

## License

MIT

---

> [notaroomba.dev](https://notaroomba.dev) &nbsp;&middot;&nbsp;
> GitHub [@NotARoomba](https://github.com/NotARoomba)

# M5StackChan-NoiseBot

<img src="https://shop.m5stack.com/cdn/shop/files/17_e897cf5e-d631-4545-af8e-2fab0e4dd588_1200x1200.webp?v=1776925002" alt="M5StackChan" width="300px"/>

Applicazione per utilizzare il [robottino M5StackChan](https://shop.m5stack.com/products/stackchan-kawaii-co-created-open-source-ai-desktop-robot) come interfaccia fisica per la webapp [NoiseBot](https://noisebot.manus.space), un sistema per monitorare il rumore e il silenzio in una classe.

Il robottino deve essere connesso a internet tramite rete Wi-Fi dedicata e comunica con l’interfaccia web di NoiseBot tramite il [protocollo MQTT](https://mqtt.org/).

### 📋 Requisiti
Prima di iniziare, assicurarsi di avere:
* Un robottino M5StackChan con installato [firmware UiFlow2](https://docs.m5stack.com/en/uiflow2/uiflow_web).
* L'app `Noisebot-MQTT.py` installata sul robottino
* Un hotspot Wi-Fi attivo con le seguenti credenziali:
    * Nome rete (SSID): `NoiseBot`
    * Password: `silenzio2026!`
* Accesso a un browser per utilizzare l’interfaccia web di NoiseBot (puoi usare anche uno smartphone).

### 🚀 Avvio del robottino

1. Attivare l’hotspot Wi-Fi
1. Accendere il robottino premendo brevemente il pulsante laterale (situato accanto alla porta USB-C sul lato sinistrod del robottino)
1. Avviare l’applicazione utilizzando il piccolo touchscreen del robottino:
    1. Cliccare su `APP. LIST` per visualizzare la lista delle applicazioni disponibili.
    1. Assicurarsi che sia selezionata l'applicazione `Noisebot-MQTT.py`
    1. Premere il bottone `RUN x1` per avviare l’applicazione
    1. Attendere che l’applicazione venga avviata.

1. Da un computer, tablet o smartphone con accesso al browser, aprire [l’interfaccia web di NoiseBot](https://noisebot.manus.space)

1. Avviare il monitor assicurandosi di concedere l’autorizzazione all’utilizzo del microfono (quando richiesto)

Il robottino ora fungerà da interfaccia fisica al sistema, mentre il sito web permetterà di controllare e configurare il comportamento di NoiseBot, tra cui la sensibilità del microfono, la durata del rumore elevato e la durata del silenzio.

### 🔄 Spegnimento, riavvio e risoluzione dei problemi

Per spegenere il robot, tenere premuto il pulsante di accensione per 6 secondi. Il pulsante si trova accanto alla porta USB-C sul lato sinistro.

Se il robottino non reagisce più ai comandi, si blocca oppure non si muove correttamente, è possibile effettuare un reset.

1. Premere brevemente il pulsante `RESET` situato accanto allo slot per la scheda microSD sul lato inferiore del dispositivo.
1. Attendere il riavvio del dispositivo.
1. Avviare nuovamente l’applicazione come spiegato precedentemente.

Se il robottino continua a non funzionare correttamente, verificare che:
* L’hotspot Wi-Fi NoiseBot sia acceso e configurato correttamente.
* La password dell’hotspot sia corretta.
* Il robottino sia connesso alla rete Wi-Fi (vedi icona 🛜)

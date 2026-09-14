# Tuya Device Inspector

A Home Assistant integration that reads a Tuya device's description from the cloud and writes it to a file you can attach to an issue.

It exists so that adding support for a new device to another integration does not require anyone to learn the Tuya API Explorer. Install this, pick your device, press a button, attach the file.

It reads only. No commands are ever sent to your devices.

## What it collects

- **Device record** — product id, category, model, online state
- **Things data model** — every datapoint with its id, type, access mode, accepted range or enum values, and the manufacturer's own description of what it does
- **Specification** — the functions and status list, keyed by code
- **Current properties** — what each datapoint reads right now

The data model is the valuable part. Its descriptions come from the manufacturer and often explain behaviour that is otherwise only discoverable by experiment, such as which settings a device forgets when it loses power. They are usually in Chinese.

The product id identifies the model: it is assigned per product by the manufacturer, so every unit of the same model shares it, regardless of what anyone has named their device.

## What it leaves out

Local keys, account identifiers, the owner's public IP address and GPS coordinates are stripped before the file is written. A local key allows direct control of a device on your network, and Tuya returns one for every device in the project, so this is not a theoretical concern.

Nothing about your Home Assistant installation is included — not the version, not your other integrations. This is why the integration writes its own file rather than using Home Assistant's diagnostics download, which always includes that information.

The device id is kept deliberately. It is useless without the local key or your account credentials, and it lets whoever reads the file match it to your report.

Read the file before posting it if you would rather check for yourself.

## Requirements

- Home Assistant 2024.8 or newer
- A Tuya IoT Platform cloud project, which is free
- Your device already set up in the Smart Life or Tuya app

## Setting up Tuya

1. Create an account at [iot.tuya.com](https://iot.tuya.com) and log in.
2. Go to **Cloud** > **Development** and click **Create Cloud Project**. Choose the data center matching where your Smart Life account is registered — the app shows this under **Me** > **Settings** > **Account and Security** > **Region**. The wrong data center will fail to authenticate.
3. Once created, note the **Access ID** and **Access Secret** on the project's Overview tab.
4. Go to the **Devices** tab, then **Link App Account**, and scan the QR code with the Smart Life app (**Me** > the scan icon, top right).
5. On the **Service API** tab, confirm **IoT Core** is subscribed. It is free, but the trial expires periodically and needs renewing.

## Installation

### HACS

1. HACS > three-dot menu > **Custom repositories**
2. Add `https://github.com/Me-Is-Andy/Tuya-Device-Inspector` as an **Integration**
3. Install, then restart Home Assistant

### Manual

Copy `custom_components/tuya_inspector` into your `config/custom_components/` directory and restart.

## Using it

1. **Settings** > **Devices & Services** > **Add Integration** > **Tuya Device Inspector**
2. Enter your Access ID, Access Secret and data center
3. Pick your device from the list
4. Open the device page and press **Export device details**
5. A notification appears with a download link

To inspect another device, add the integration again and pick a different one.

Once you have the file you can remove the integration; it holds no state.

There is also an action, `tuya_inspector.export`, if you would rather run it from Developer Tools or a script.

## Notes

**Where the file goes.** It is written to `config/www/`, which Home Assistant serves at `/local/` without authentication. Anyone who knows the URL can read it, which is part of why the contents are redacted. The same filename is reused on every export, so repeated runs do not leave a pile behind.

**If the download link does nothing.** The notification includes the file's address as plain text underneath. Open that directly. The Home Assistant frontend sometimes intercepts the link and returns you to your dashboard instead.

**It creates two entities.** A button to run the export, and a diagnostic sensor showing the product id.

**Not every device answers every call.** Some firmware reports a data model and no specification, or the reverse. A call that fails is recorded as an error inside the file rather than aborting the whole export.

**Devices are listed 20 at a time.** That is Tuya's documented maximum for this endpoint; a project with more devices will show a truncated list.

## License

MIT
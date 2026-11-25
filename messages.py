"""Backend messages in German and English. The UI sends its language via the X-ModFerry-Lang header."""

MESSAGES = {
    'err.localOnly': {'de': 'Nur lokale Zugriffe sind erlaubt.', 'en': 'Only local access is allowed.'},
    'err.badOrigin': {'de': 'Ungültiger Request-Ursprung.', 'en': 'Invalid request origin.'},
    'err.tokenField': {'de': 'Unbekanntes Token-Feld.', 'en': 'Unknown token field.'},
    'err.tokenText': {'de': 'Token muss Text sein.', 'en': 'Token must be text.'},
    'err.platform': {'de': 'Unbekannte Plattform.', 'en': 'Unknown platform.'},
    'err.cfTokenMissing': {'de': 'CurseForge-Token fehlt.', 'en': 'CurseForge token missing.'},
    'err.versionsFailed': {'de': 'CurseForge-Versionen konnten nicht geladen werden: {detail}', 'en': 'Could not load CurseForge versions: {detail}'},
    'err.versionsEmpty': {'de': 'Die Versions-API lieferte keine Versionsliste.', 'en': 'The versions API returned no version list.'},
    'err.noFiles': {'de': 'Keine Dateien ausgewählt.', 'en': 'No files selected.'},
    'err.projectType': {'de': 'Unbekannter Projekttyp.', 'en': 'Unknown project type.'},
    'err.fileType': {'de': 'Dateityp für {type} nicht erlaubt: {name} (erlaubt: {allowed})', 'en': 'File type not allowed for {type}: {name} (allowed: {allowed})'},
    'err.fileName': {'de': 'Ungültiger Dateiname.', 'en': 'Invalid file name.'},
    'err.fileTooLarge': {'de': 'Datei überschreitet {mb} MB: {name}', 'en': 'File exceeds {mb} MB: {name}'},
    'err.fileEmpty': {'de': 'Leere Datei: {name}', 'en': 'Empty file: {name}'},
    'err.profileName': {'de': 'Profilname muss 1 bis 80 Zeichen enthalten.', 'en': 'Profile name must be 1 to 80 characters.'},
    'err.profileInvalid': {'de': 'Ungültiges Profil.', 'en': 'Invalid profile.'},
    'err.relationsList': {'de': '{file}: Abhängigkeiten müssen eine Liste mit höchstens 100 Einträgen sein.', 'en': '{file}: dependencies must be a list with at most 100 entries.'},
    'err.relationEntry': {'de': '{file}: Ungültiger Abhängigkeitseintrag.', 'en': '{file}: invalid dependency entry.'},
    'err.relationType': {'de': '{file}: Unbekannter Relationstyp: {kind}', 'en': '{file}: unknown relation type: {kind}'},
    'err.relationInclude': {'de': '{file}: „Include“ wird vom CurseForge-Upload-Endpunkt nicht unterstützt. Bitte entfernen; es wird nicht in einen anderen Typ umgedeutet.', 'en': '{file}: "Include" is not supported by the CurseForge upload endpoint. Please remove it; it is never silently converted to another type.'},
    'err.relationSlug': {'de': '{file}: CurseForge-Projekt-Slug fehlt oder ist ungültig (z. B. cloth-config).', 'en': '{file}: CurseForge project slug missing or invalid (e.g. cloth-config).'},
    'err.relationId': {'de': '{file}: Projekt-ID der Abhängigkeit muss numerisch sein.', 'en': '{file}: dependency project ID must be numeric.'},
    'err.cfJobBasics': {'de': 'CurseForge-Token und numerische Projekt-ID sind erforderlich.', 'en': 'CurseForge token and numeric project ID are required.'},
    'err.cfProject': {'de': 'Numerische CurseForge-Projekt-ID erforderlich.', 'en': 'Numeric CurseForge project ID required.'},
    'err.releaseType': {'de': '{file}: Ungültiger Release-Typ.', 'en': '{file}: invalid release type.'},
    'err.entries': {'de': 'Bitte 1 bis 100 Dateien auswählen.', 'en': 'Please select 1 to 100 files.'},
    'err.changelog': {'de': 'Ungültiges Changelog.', 'en': 'Invalid changelog.'},
    'err.fileGone': {'de': 'Eine hochzuladende Datei ist nicht mehr vorhanden. Bitte erneut hinzufügen.', 'en': 'A file to upload no longer exists. Please add it again.'},
    'err.cfVersions': {'de': '{file}: Mindestens eine gültige Minecraft-Version auswählen.', 'en': '{file}: select at least one valid Minecraft version.'},
    'err.serverPack': {'de': '{file}: Server-Pack nicht gefunden oder kein .zip.', 'en': '{file}: server pack not found or not a .zip.'},
    'err.noneForPlatform': {'de': 'Keine Dateien für {platform} aktiviert.', 'en': 'No files enabled for {platform}.'},
    'err.busy': {'de': 'Es läuft bereits ein Upload.', 'en': 'An upload is already running.'},
    'err.unknownJob': {'de': 'Unbekannter Upload.', 'en': 'Unknown upload.'},
    'err.mrDepList': {'de': '{file}: Ungültige Modrinth-Abhängigkeitsliste.', 'en': '{file}: invalid Modrinth dependency list.'},
    'err.mrDepEntry': {'de': '{file}: Ungültige Abhängigkeit.', 'en': '{file}: invalid dependency.'},
    'err.mrDepType': {'de': '{file}: {kind} ist keine unterstützte Modrinth-Abhängigkeit. Entfernen oder Modrinth für diese Datei deaktivieren.', 'en': '{file}: {kind} is not a supported Modrinth dependency. Remove it or disable Modrinth for this file.'},
    'err.mrDepId': {'de': '{file}: Für jede Modrinth-Abhängigkeit ist eine Modrinth-Projekt-ID oder ein Slug erforderlich.', 'en': '{file}: every Modrinth dependency needs a Modrinth project ID or slug.'},
    'err.mrJobBasics': {'de': 'Modrinth-Token und gültige Modrinth-Projekt-ID/Slug erforderlich.', 'en': 'Modrinth token and a valid Modrinth project ID/slug are required.'},
    'err.mrProject': {'de': 'Gültige Modrinth-Projekt-ID oder Slug erforderlich.', 'en': 'Valid Modrinth project ID or slug required.'},
    'err.mrVersions': {'de': '{file}: Modrinth Minecraft-Version(en) fehlen oder sind ungültig.', 'en': '{file}: Modrinth Minecraft version(s) missing or invalid.'},
    'err.mrLoaders': {'de': '{file}: Modrinth-Loader fehlen oder passen nicht zum Projekttyp ({allowed}).', 'en': '{file}: Modrinth loaders missing or not valid for this project type ({allowed}).'},
    'err.mrNumber': {'de': '{file}: Modrinth-Versionsnummer fehlt.', 'en': '{file}: Modrinth version number missing.'},
    'err.mrNumberDup': {'de': 'Modrinth-Versionsnummer doppelt vergeben: {number}', 'en': 'Modrinth version number used twice: {number}'},
    'err.mrEnv': {'de': '{file}: Ungültiges Modrinth-Environment.', 'en': '{file}: invalid Modrinth environment.'},
    'err.mrStatus': {'de': 'Ungültiger Modrinth-Status.', 'en': 'Invalid Modrinth status.'},
    'err.mrResolve': {'de': 'Modrinth-Projekt-ID konnte nicht geprüft werden: {detail}', 'en': 'Could not verify Modrinth project ID: {detail}'},
    'err.mrTags': {'de': 'Modrinth-Tags nicht erreichbar: {detail}', 'en': 'Modrinth tags unavailable: {detail}'},
    'err.markdown': {'de': 'Markdown-Changelog muss Text mit maximal 200.000 Zeichen sein.', 'en': 'Markdown changelog must be text with at most 200,000 characters.'},
    'err.masterShort': {'de': 'Master-Passwort benötigt mindestens 12 Zeichen.', 'en': 'Master password needs at least 12 characters.'},
    'err.storeLocked': {'de': 'Token-Speicher gesperrt: Master-Passwort eingeben.', 'en': 'Token store locked: enter the master password.'},
    'err.dpapi': {'de': 'Windows DPAPI: Verschlüsselung/Entschlüsselung fehlgeschlagen.', 'en': 'Windows DPAPI: encryption/decryption failed.'},
    'err.storeScheme': {'de': 'Token-Datei gehört zu anderem Betriebssystem/Verschlüsselungsmodus.', 'en': 'Token file belongs to a different OS/encryption mode.'},
    'err.wrongPassword': {'de': 'Falsches Master-Passwort oder beschädigte Token-Datei.', 'en': 'Wrong master password or damaged token file.'},
    'up.uploading': {'de': 'Wird hochgeladen …', 'en': 'Uploading …'},
    'up.pending': {'de': 'Wartet …', 'en': 'Waiting …'},
    'up.cfDone': {'de': 'Hochgeladen (Datei-ID {id})', 'en': 'Uploaded (file ID {id})'},
    'up.cfServerPack': {'de': 'Hochgeladen (Datei-ID {id}, Server-Pack {sid})', 'en': 'Uploaded (file ID {id}, server pack {sid})'},
    'up.cfServerPackFailed': {'de': 'Hauptdatei {id} hochgeladen, Server-Pack fehlgeschlagen: {detail}', 'en': 'Main file {id} uploaded, server pack failed: {detail}'},
    'up.mrDone': {'de': 'Modrinth-Version {id}', 'en': 'Modrinth version {id}'},
    'up.noId': {'de': 'Antwort ohne ID: {detail}', 'en': 'Response without ID: {detail}'},
}

LANGS = ('de', 'en')


class UserError(ValueError):
    """An error with a translatable message key."""

    def __init__(self, key, **params):
        super().__init__(key)
        self.key = key
        self.params = params

    def text(self, lang):
        return t(self.key, lang, **self.params)


def t(key, lang='de', **params):
    entry = MESSAGES.get(key)
    if not entry:
        return key
    template = entry.get(lang) or entry['de']
    try:
        return template.format(**params)
    except (KeyError, IndexError):
        return template


def pick_lang(header_value, accept_language=''):
    value = (header_value or '').strip().lower()[:2]
    if value in LANGS:
        return value
    for part in (accept_language or '').split(','):
        code = part.strip().lower()[:2]
        if code in LANGS:
            return code
    return 'en'

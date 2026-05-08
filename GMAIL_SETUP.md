# Gmail-drafting — Installationsguide

Denna guide beskriver hur du konfigurerar lonespec-splitter för att automatiskt skapa Gmail-utkast för lönespec-mottagare.

## Förutsättningar

- lonespec-splitter v0.2.0+
- Google Workspace-account (arbetsgivarens)
- Admin-åtkomst till Google Cloud Console för din organisation

## Steg 1: Skapa ett Google Cloud-projekt

1. Gå till [Google Cloud Console](https://console.cloud.google.com/).
2. Klicka på **Välj ett projekt** → **Nytt projekt**.
3. Namnge projektet (t.ex., `lonespec-splitter`).
4. Skapa projektet.

## Steg 2: Aktivera API:er

1. I Cloud Console, sök efter **Admin SDK**.
2. Klicka på resultatet, klicka **Aktivera**.
3. Sök efter **Gmail API**.
4. Klicka på resultatet, klicka **Aktivera**.

## Steg 3: Skapa en tjänstekonto (Service Account)

1. Gå till **IAM och administration** → **Tjänstekonton**.
2. Klicka på **Skapa tjänstekonto**.
3. Fyll i:
   - **Kontonamn:** `lonespec-splitter`
   - **Konto-ID:** `lonespec-splitter` (autofyllt)
4. Klicka **Skapa och fortsätt**.
5. (Valfritt) Bevilja roller — du kan hoppa över detta och fortsätta.
6. Klicka **Fortsätt**.

## Steg 4: Skapa en JSON-nyckel

1. På sidan för tjänstekontot (`lonespec-splitter`), gå till fliken **Nycklar**.
2. Klicka **Lägg till nyckel** → **Skapa ny nyckel**.
3. Välj **JSON** som nyckeltyp.
4. Klicka **Skapa** — filen `*.json` laddas ner automatiskt.
5. **Spara filen säkert** (t.ex., i din hemkatalog eller ett lösenordshanteringssystem).

## Steg 5: Delegera behörighet (Domain-Wide Delegation)

1. Gå till sidan för tjänstekontot, fliken **Detaljer**.
2. Scroll ned, hitta **Klient-ID** och **Klient-e-post** — kopiera båda värdena.
3. Gå till **Google Workspace Admin Console** (admin.google.com).
4. Gå till **Säkerhet** → **API-kontroller** → **Domänomfattande delegering**.
5. Klicka **Lägg till nytt** och fyll i:
   - **Klient-ID:** (värde från steg 2)
   - **OAuth-omfattningar:** `https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/admin.directory.user.readonly`
6. Klicka **Godkänd**.

## Steg 6: Konfigurera lonespec-splitter

1. Kopiera filen `gmail_config.yaml.example` till `gmail_config.yaml`:
   ```bash
   cp gmail_config.yaml.example gmail_config.yaml
   ```

2. Redigera `gmail_config.yaml`:
   ```yaml
   enabled: true
   workspace_domain: "ditt-företag.se"  # Din Workspace-domän
   service_account_key_path: "/path/to/your/service_account_key.json"
   ```

3. Ersätt värdena:
   - `workspace_domain`: Din Google Workspace-domän (t.ex., `company.se`).
   - `service_account_key_path`: Absolut sökväg till JSON-nyckeln från steg 4.

4. **Viktigt:** Lägg inte till `gmail_config.yaml` eller JSON-nyckeln i git-repot. De är redan i `.gitignore`.

## Steg 7: Testa konfigurationen

```bash
python -m lonespec_splitter input.pdf output_dir/ --with-gmail --gmail-config ./gmail_config.yaml
```

Om allt är konfigurerat rätt:
- PDF:en splittas normalt.
- För varje person skapas en Gmail-utkast i din Gmail-inkorgs **Utkast**-mapp.
- Logg skrivs till `output_dir/_split_log.txt`.

## Felsökning

### Fel: "Config file not found"
- Kontrollera att vägen till `gmail_config.yaml` är korrekt.

### Fel: "Service account key not found"
- Kontrollera att vägen till JSON-nyckeln i `gmail_config.yaml` är korrekt.
- Nyckeln är en känslig fil — spara den utanför repot.

### Fel: "Directory lookup failed" eller ingen utkast skapas
- Kontrollera att tjänstekontot har delegerad behörighet (steg 5).
- Verifiera att `workspace_domain` är korrekt.
- Kontrollera att namnen i PDF:en matchar namn i Workspace-katalogen.

### Utkast skapas inte för vissa personer
- Namn på lönespec matchar inte Workspace-katalogens namn exakt — logg visar varning.
- Om namn är känt-felaktigt kan du manuellt öppna utkastet och korrigera mottagaren innan du skickar.

## Sekretesspolicy

- JSON-nyckeln är **mycket känslig** — den ger full åtkomst till Gmail och katalog. Lagra den säkert och dela aldrig.
- Drafts skapas under det tjänstekonto-e-postadresser som konfigurerades, **ej** under din personliga Gmail.
- Alla drafts är märkta med namnet på den ursprungliga lönespec-PDF:en i loggen.

## Support

Vid problem, se `CHANGELOG.md` och GitHub-issuer på https://github.com/gitjoda71/lonespec-splitter.

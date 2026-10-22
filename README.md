# discordinio
Zbiór botów Discorda. Każdy bot ma własny folder i własny workflow w `.github/workflows/`.

| Bot | Co robi | Secret |
|---|---|---|
| `wow-forever-news-bot` | newsy o WoW: Forever z Wowheada, co 5 min | `WOW_FOREVER_WEBHOOK` |

## Dodawanie nowego bota
1. Nowy folder `nazwa-bota/` z kodem i własnym `.env.example`.
2. Workflow `.github/workflows/nazwa-bota.yml` (skopiuj istniejący, zmień nazwę, folder i secret).
3. Settings -> Secrets and variables -> Actions: dodaj secret z webhookiem.

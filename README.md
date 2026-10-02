# BilanKine (MVP Streamlit)

Application Streamlit de support au bilan kinésithérapique (documentation + raisonnement clinique, non diagnostique).

## Lancement

```bash
streamlit run bilan_app.py
```

## Limites cliniques et sécurité

- Utilisation réservée à un professionnel formé ; ne pas utiliser en auto-évaluation patient.
- Les red flags sont des aides au dépistage et à l’orientation selon le contexte et les procédures locales.
- Les seuils/tests sont paramétrables ; ils ne constituent pas des normes universelles.
- Ne pas saisir de données patient réelles identifiantes dans un environnement non sécurisé.
- Aucune transmission vers un service distant n’est requise.

## Références et limites

- Laslett et al., 2005 (PMID 16038856) : <https://pubmed.ncbi.nlm.nih.gov/16038856/>
- Laslett et al., 2003 (PMID 12775204) : <https://pubmed.ncbi.nlm.nih.gov/12775204/>
- NICE NG59 (lombalgie/sciatique) : <https://www.nice.org.uk/guidance/ng59>
- McKenzie Institute (formulaires lombaire/cervicale 2020) : inspiration structurelle uniquement.
- Littérature McGill / Childs / Liebenson sur Sorensen, trunk flexor, side bridge : protocoles utiles, normes variables selon population/protocole.

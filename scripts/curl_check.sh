#!/bin/sh
# Live HTTP check against a deploy: clean URL -> 200 with self canonical, .html -> one 308 hop to clean URL.
# Usage: scripts/curl_check.sh https://<deploy-host>
# Protected preview: vercel env run -- sh scripts/curl_check.sh https://<preview-host>
# (sends $VERCEL_OIDC_TOKEN as the Trusted Sources header; never printed)
BASE=$1
TMP=$(mktemp)
fail=0
c() { if [ -n "$VERCEL_OIDC_TOKEN" ]; then curl -H "x-vercel-trusted-oidc-idp-token: $VERCEL_OIDC_TOKEN" "$@"; else curl "$@"; fi; }
for slug in "" coffee-menu donuts-menu breakfast-menu apple-fritter-donut latte brewed-coffee \
            peach-lemonade-quencher 6-assorted-donuts are-tim-hortons-donuts-baked-or-fried blog; do
  code=$(c -s -o "$TMP" -w '%{http_code}' "$BASE/$slug")
  canon=$(grep -o '<link rel="canonical" href="[^"]*"' "$TMP" | sed 's/.*href="//;s/"//')
  [ -z "$slug" ] && want=https://timhortonsdonuts.com/ || want=https://timhortonsdonuts.com/$slug
  line="/$slug  clean:$code canon:$([ "$canon" = "$want" ] && echo ok || echo "BAD($canon)")"
  [ "$code" = 200 ] && [ "$canon" = "$want" ] || fail=1
  if [ -n "$slug" ]; then
    hop=$(c -s -o /dev/null -w '%{http_code} %{redirect_url}' "$BASE/$slug.html")
    final=$(c -sL -o /dev/null -w '%{http_code} %{num_redirects}' "$BASE/$slug.html")
    line="$line  .html:${hop#* }->${hop%% *}  follow:$final"
    [ "$hop" = "308 $BASE/$slug" ] && [ "$final" = "200 1" ] || fail=1
  fi
  echo "$line"
done
code=$(c -s -o /dev/null -w '%{http_code}' "$BASE/seo-research/Task10_Master_Checklist.csv")
echo "seo-research exposed? $code (want 404)"; [ "$code" = 404 ] || fail=1
rm -f "$TMP"
[ $fail = 0 ] && echo "curl_check: PASS" || { echo "curl_check: FAIL"; exit 1; }

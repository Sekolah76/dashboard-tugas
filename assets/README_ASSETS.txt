DANA Insight Command Center — Asset Pack

Files:
- dana_logo_wordmark_header_480x120.png: header/sidebar logo. Display around 140–180 px wide.
- dana_logo_wordmark_1200x300.png: high-res logo/landing page.
- dana_hero_banner_1920x520.png: dashboard top hero/banner background. Suggested height 220–300 px in dashboard, cover/right center.
- dana_hero_full_1600x900.png: landing/lobby hero illustration.
- dana_wallet_cluster_720x720.png: decorative card/section illustration.
- dana_wallet_cluster_480x480.png: smaller decorative version.
- dana_mobile_mockup_720x960.png: mobile/responsive/lobby illustration.
- dana_mobile_mockup_360x480.png: smaller mobile version.

Recommended project path:
assets/brand/dana_logo_wordmark_header_480x120.png
assets/illustrations/dana_hero_banner_1920x520.png
assets/illustrations/dana_hero_full_1600x900.png
assets/illustrations/dana_wallet_cluster_720x720.png
assets/illustrations/dana_mobile_mockup_720x960.png

Use with Streamlit:
st.image(str(ASSETS_DIR / 'brand' / 'dana_logo_wordmark_header_480x120.png'), width=160)

For hero background use base64 CSS, not st.image, so the image becomes a true banner.

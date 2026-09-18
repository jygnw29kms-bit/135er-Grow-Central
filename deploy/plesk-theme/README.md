# Grow-Central branding for Plesk

Prepared for Plesk Obsidian 18.0.80. This theme uses the website palette
(#02070a, #041014, #2ae5ff, #71ff3b) and the existing project logo.
It changes decorative styles; Plesk routes, layout, permissions and services
remain controlled by Plesk. Warning and error colors retain their native styles.

The Plesk administrator menu link was created through Custom Buttons:
Grow-Central → /modules/grow-central/, only visible to the administrator,
opened inside Plesk without a frame, without URL credential parameters.

## Server installation

Use the official Plesk theme utility as administrator. First export the
current branding for rollback and a default theme as the build basis.
Keep these archives outside public document roots.

```sh
plesk bin branding_theme -p -name default -vendor admin -destination /root/grow-central-branding-backup.zip
plesk bin branding_theme -p -name default -destination /root/plesk-default-theme.zip
python3 deploy/plesk-theme/build_theme.py --base /root/plesk-default-theme.zip --logo website/assets/brand/135er-grow-central-lockup-v0.9.png --output /root/grow-central-theme.zip
plesk bin branding_theme -i -vendor admin -source /root/grow-central-theme.zip
```

If the current account uses a previously named custom theme, export that name
instead of default for the rollback archive. If Plesk reports an empty branding
theme, record that state before installing. The default export is still required.

Sign out and sign in to activate the installed custom theme.
Check the sidebar link, logo, primary buttons, dialogs, tables, mobile navigation,
and accessible focus states. Source CSS is prepared but full server visual QA
and installation are pending approved server access.

To revert, reinstall the exported prior branding archive. If the prior branding
was empty, use the official branding_theme uninstall action for this theme.

References:
- https://docs.plesk.com/en-US/obsidian/administrator-guide/customizing-the-plesk-interface/using-custom-themes.70906/
- https://docs.plesk.com/en-US/obsidian/administrator-guide/customizing-the-plesk-interface/using-custom-themes/installing-themes-to-plesk.70908/

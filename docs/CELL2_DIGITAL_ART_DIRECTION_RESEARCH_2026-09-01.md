# Cell 2 digital art-direction research

Checked 2026-09-01. This note records principles, not competitor assets or layouts.

## Sources reviewed

- Apple Human Interface Guidelines, Accessibility: https://developer.apple.com/design/human-interface-guidelines/accessibility
- Oura Member Care, How to Use the Oura App, updated 2026-06-25: https://support.ouraring.com/hc/en-us/articles/360058599753-How-to-Use-the-Oura-App
- Oura product/app material: https://ouraring.com/app and https://ouraring.com/how-it-works
- WHOOP product guidance pattern, Strain Target: https://www.whoop.com/us/en/thelocker/strain-coach/

## Distilled principles

1. The companion app should answer current state and next action before exposing detail. Oura's current app structure emphasizes an at-a-glance Today surface; WHOOP's guidance pattern turns state into an actionable target. Masck One therefore leads with device readiness and one primary cycle action, not analytics cards.
2. Hardware should remain the visual anchor. Product form is used as a status object, not decorative 3D wallpaper. The first prototype deliberately uses a restrained silhouette until controlled geometry can be consumed safely.
3. Accessibility is a design input. Apple recommends adaptable interfaces, larger text support, non-color state cues, and WCAG-informed contrast. The prototype uses semantic landmarks, visible focus, a 48px-class primary action, explicit text status, and reduced-motion behavior.
4. Web storytelling should sequence comprehension: proposition, system logic, zones, service, access. Motion will be added only where it explains a controlled mechanism or spatial relationship. Static fallback remains the authored baseline.
5. Non-copying rule: no competitor screen, copy, geometry, icon, animation or trade dress is reproduced. Masck One's visual grammar is derived from compliant versus rigid fields, controlled seams, muted CMF, and the released shared visual contract.

## Current visual hypothesis

Light editorial web surface: warm mineral `#e8e5dc`, carbon `#1d211f`, restrained green `#314f38`. Dark app surface: `#171917` with soft mineral text `#f0eee7` and pale functional green `#d6e7cf`. These values match the released Cell 2 visual-system fixture and remain presentation-only, not CMF evidence.

Display hierarchy uses low-weight, tightly tracked large type against compact technical labels. Shape grammar favors continuous asymmetric facial fields and deliberate seam lines over generic card stacks. The app uses one large device field plus one primary action; secondary care information is linear rather than dashboard-like.

## Next quality gates

Bind both workspaces to generated target manifests and verify both `visual_system_sha256` and `payload_sha256`. Replace the abstract silhouette only when controlled product geometry is available. Add GSAP/WebGL only after the motion contract is released and endpoints/provenance can be consumed without inventing mechanism states. Run responsive, keyboard, text-scaling, contrast, reduced-motion and low-power visual QA before any launch claim.
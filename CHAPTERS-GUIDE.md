# Naye chapters kaise add karein (code change NAHI chahiye)
1. Apni chapter JSON ka naam rakho: `chapter_<naam>.json` (e.g. `chapter_physics_rotation.json`)
2. Format wahi rakho: `meta.subject` = "Physics"/"Chemistry"/"Biology", `questions` array mein har question:
   `question, options(4), answer_index(1-4) ya answer("A"-"D"), needs_review, image(https URL ya null)`
3. Images ho to pehle `images/` folder mein PNG upload karo, phir question ki `image` mein poora URL:
   `https://raw.githubusercontent.com/malikravish35-star/SPARTA_NEETQUIZ/main/images/<file>.png`
4. File repo root mein upload karo -> Render redeploy -> bot khud load kar lega.
Note: needs_review=true ya 4 options se kam wale questions skip ho jaate hain.

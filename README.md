# Janwar Mandi - Livestock Marketplace (Flask)

Log apne janwar ke ads lagate hain, admin approve karta hai, aur approved ad
(agar Facebook configure ho) Facebook Page par auto-post ho jata hai.

## Setup (Windows)
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # phir .env mein SECRET_KEY set karein
flask --app run create-admin  # apna admin account banayein
python run.py
```
Browser mein kholein: http://127.0.0.1:5000

Tables aur categories pehli baar run par khud ban jati hain.

## Facebook auto-post
1. Facebook Page banayein aur Meta developer app create karein.
2. Page access token lein (permissions: pages_manage_posts, pages_read_engagement).
3. `.env` mein FB_PAGE_ID aur FB_PAGE_ACCESS_TOKEN daalein.
4. Deploy ke baad PUBLIC_BASE_URL set karein (Facebook ko photo ka public URL chahiye;
   localhost par sirf text/link post hogi).

Admin panel (/admin) mein approve karte hi ad Page par post hota hai.
Fail ho to error wahin nazar aata hai aur "Post to Facebook" se dobara try kar sakte hain.

## Structure
- app/models.py              database tables
- app/routes/auth.py         signup, login, logout
- app/routes/ads.py          home + search, ad detail, post ad, my ads, favorites
- app/routes/admin.py        approve / reject / retry Facebook
- app/services/facebook.py   Facebook Graph API posting
- app/services/publish.py    approve + post logic
- app/templates, app/static  HTML, CSS, JS

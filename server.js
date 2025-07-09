 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 

 const express = require('express');
 const Stripe = require('stripe');
+const config = require('./config');
 
 const app = express();
-const stripe = Stripe(process.env.STRIPE_SECRET_KEY);
+const stripe = Stripe(config.stripeSecretKey);
 
 app.use(express.static('.'));
 app.use(express.json());
 
 app.post('/create-checkout-session', async (req, res) => {
   const { priceId } = req.body;
   try {
     const session = await stripe.checkout.sessions.create({
       mode: 'payment',
       line_items: [{ price: priceId, quantity: 1 }],
       success_url: `${req.headers.origin}/?success=true`,
       cancel_url: `${req.headers.origin}/?canceled=true`,
     });
     res.json({ url: session.url });
   } catch (err) {
     console.error(err);
     res.status(500).json({ error: 'Unable to create session' });
   }
 });
 
-const PORT = process.env.PORT || 4242;
-app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
+app.listen(config.port, () => console.log(`Server running on port ${config.port}`));
 
EOF
)

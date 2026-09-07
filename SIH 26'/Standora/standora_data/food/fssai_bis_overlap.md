# FSSAI vs BIS — Critical Nuance for Food Products

Source: https://fssai.gov.in/
Source: https://www.bis.gov.in/product-certification/product-certification-overview/

## Core rule the assistant must follow

**FSSAI** is the primary regulator for food safety, standards, licensing, and
enforcement for packaged food products, under the FSS Act, 2006.

**BIS** publishes Indian Standards for many food items (e.g., packaged
drinking water, edible oils, spices), but these are **typically voluntary**
unless a specific Quality Control Order (QCO) has been notified making BIS
certification mandatory for that item.

## Routing logic for the assistant

When a user asks "is BIS certification required for [food product]?":
1. First check if a QCO has been notified for that specific product.
2. If a QCO exists → BIS certification is mandatory; cite the QCO.
3. If no QCO exists → the applicable IS standard (if any) is voluntary;
   the user should be directed to FSSAI licensing/registration requirements
   instead, since that is what's actually mandatory.
4. Never assert that a food product needs mandatory BIS marking without
   confirming a QCO exists — this is the single biggest accuracy risk in
   this category.

## Example

- Packaged drinking water (IS 14543): commonly cited standard, but the
  assistant should confirm current QCO status before telling a user
  certification is "mandatory" — treat this as needing verification rather
  than asserting outright.
- Edible oils (IS 14309, IS 11069, IS 11068, etc.): generally FSSAI-regulated;
  BIS standards exist under the FAD 13 committee but are typically voluntary.

---
DRAFT — expand with the exact current QCO list for food items once verified
directly on the BIS QCO notification page (QCO status changes over time, so
this should be double-checked close to the demo date, not just once now).

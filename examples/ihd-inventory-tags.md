---
title: Inventory Tag
theme: ihd
paper: letter
profile: laser
masthead: false
footer: false
margin: 11mm
fit: 1
fill: true
columns: 1
# Every dimension below is a multiple of --ps-scale, so the fit solver can grow
# the tags until six of them exactly fill the sheet. Hard-coded mm here would
# opt the whole sheet out of fitting — which is the one mistake this tool exists
# to stop you making.
css: |
  .tags { display: grid; grid-template-columns: 1fr 1fr;
          gap: calc(7mm * var(--ps-scale)) calc(7.5mm * var(--ps-scale)); }
  .tag { border: 0.6pt dashed #6a6a70; break-inside: avoid;
         padding: calc(5.5mm * var(--ps-scale)) calc(6mm * var(--ps-scale)); }
  .tag .crest { text-align: center; margin-bottom: calc(3.4mm * var(--ps-scale)); }
  .tag .crest img { height: calc(15mm * var(--ps-scale)); }
  .tag .crest .cap { font-family: var(--ps-mono); font-size: calc(6pt * var(--ps-scale));
                     letter-spacing: 0.28em; text-transform: uppercase;
                     margin-top: calc(1mm * var(--ps-scale)); }
  .tag .f { margin-bottom: calc(3.3mm * var(--ps-scale)); }
  .tag .f b { font-family: var(--ps-mono); font-size: calc(5.6pt * var(--ps-scale));
              letter-spacing: 0.17em; text-transform: uppercase; color: #34343a; display: block; }
  .tag .f i { display: block; border-bottom: 0.7pt solid #101010;
              height: calc(4.7mm * var(--ps-scale)); }
  .tag .row { display: grid; grid-template-columns: 1fr 1fr; gap: calc(4mm * var(--ps-scale)); }
  .tag .no { font-family: var(--ps-mono); font-size: calc(5.4pt * var(--ps-scale));
             letter-spacing: 0.15em; text-align: right; color: #6a6a70;
             margin-top: calc(1.5mm * var(--ps-scale)); }
---

<div class="tags">

<div class="tag">
  <div class="crest"><img src="../assets/ihd-monogram.png" alt=""><div class="cap">Inventory Tag</div></div>
  <div class="f"><b>Item</b><i></i></div>
  <div class="row">
    <div class="f"><b>Department</b><i></i></div>
    <div class="f"><b>Acquired</b><i></i></div>
  </div>
  <div class="f"><b>Storage location</b><i></i></div>
  <div class="no">IHD-________</div>
</div>

<div class="tag">
  <div class="crest"><img src="../assets/ihd-monogram.png" alt=""><div class="cap">Inventory Tag</div></div>
  <div class="f"><b>Item</b><i></i></div>
  <div class="row">
    <div class="f"><b>Department</b><i></i></div>
    <div class="f"><b>Acquired</b><i></i></div>
  </div>
  <div class="f"><b>Storage location</b><i></i></div>
  <div class="no">IHD-________</div>
</div>

<div class="tag">
  <div class="crest"><img src="../assets/ihd-monogram.png" alt=""><div class="cap">Inventory Tag</div></div>
  <div class="f"><b>Item</b><i></i></div>
  <div class="row">
    <div class="f"><b>Department</b><i></i></div>
    <div class="f"><b>Acquired</b><i></i></div>
  </div>
  <div class="f"><b>Storage location</b><i></i></div>
  <div class="no">IHD-________</div>
</div>

<div class="tag">
  <div class="crest"><img src="../assets/ihd-monogram.png" alt=""><div class="cap">Inventory Tag</div></div>
  <div class="f"><b>Item</b><i></i></div>
  <div class="row">
    <div class="f"><b>Department</b><i></i></div>
    <div class="f"><b>Acquired</b><i></i></div>
  </div>
  <div class="f"><b>Storage location</b><i></i></div>
  <div class="no">IHD-________</div>
</div>

<div class="tag">
  <div class="crest"><img src="../assets/ihd-monogram.png" alt=""><div class="cap">Inventory Tag</div></div>
  <div class="f"><b>Item</b><i></i></div>
  <div class="row">
    <div class="f"><b>Department</b><i></i></div>
    <div class="f"><b>Acquired</b><i></i></div>
  </div>
  <div class="f"><b>Storage location</b><i></i></div>
  <div class="no">IHD-________</div>
</div>

<div class="tag">
  <div class="crest"><img src="../assets/ihd-monogram.png" alt=""><div class="cap">Inventory Tag</div></div>
  <div class="f"><b>Item</b><i></i></div>
  <div class="row">
    <div class="f"><b>Department</b><i></i></div>
    <div class="f"><b>Acquired</b><i></i></div>
  </div>
  <div class="f"><b>Storage location</b><i></i></div>
  <div class="no">IHD-________</div>
</div>

</div>

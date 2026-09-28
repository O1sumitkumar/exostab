# FAQ

**exostab says "marginal". Is the system unstable?**
Not necessarily. "Marginal" means the evidence is mixed: part of the parameter range allowed by the error bars
is chaotic, or the analytic criteria fail while the integration looks regular. Read the notes under each
indicator. Resonant systems such as GJ 876 are typically marginal.

**The archive says the planets exist. How can exostab call the system unstable?**
Usually one of three things is going on: the parameters come from different publications that do not fit
together, the orbital phases are unknown and were drawn at random, or the error bars are wide. The report lists
which of these apply. Try the published orbital solution of one paper with `--from-file`.

**How long does a check take?**
About 3–8 seconds for 2–7 planets with the defaults on a recent laptop with many cores, and about 7 s (3 planets)
to 15 s (7 planets) on a single core. The analytic indicators take milliseconds.

**Why are the orbits flat (coplanar)?**
The angles between orbital planes are almost never measured. Transit and radial-velocity inclinations are
measured against the sky, not against each other.

**Can I trust the result for a billion years?**
No. The integration covers 10,000 orbits of the innermost planet by default (`--orbits` changes this). The AMD
and Hill criteria reach further but make approximations. See [Methods](methods.md).

**How do I cite exostab?**
Use the repository's `CITATION.cff` and cite the methods and the NASA Exoplanet Archive (see
[Data and assumptions](data-assumptions.md)).

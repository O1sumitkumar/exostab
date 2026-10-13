# FAQ

**exostab says "marginal". Is the system unstable?**
Not necessarily. "Marginal" means the evidence is mixed: part of the parameter range allowed by the error bars
is chaotic, or the analytic criteria fail while the integration looks regular. Read the notes under each
indicator. Resonant systems such as GJ 876 are typically marginal. A system is also marginal when every run is
regular but the outer planets complete fewer than 100 orbits or WHFast and IAS15 disagree, when one draw within
the error bars has a close encounter, when an instability rests on values that are only upper limits, when the
system has more than one star, and with `--draws 0`. The overall summary says which.

**The archive says the planets exist. How can exostab call the system unstable?**
Usually one of three things is going on: the parameters come from different publications that do not fit
together, the orbital phases are unknown and were drawn at random, or the error bars are wide. The report lists
which of these apply. Try the published orbital solution of one paper with `--from-file`. exostab never calls a
system unstable when the runs use masses or eccentricities that are only published upper limits (for the four
planets of HD 215152 the archive gives only mass limits, of 469 to 975 Earth masses), or when the system has more
than one star, of which only the host is modelled. Such systems are marginal, and the report says why.

**What does "inconclusive" mean?**
The N-body integrations could not be trusted, in the nominal run or in more than 20% of the draws: the relative
energy error exceeded 10⁻⁵, or a planet passed so close to the star that tides, general relativity and the size
of the star, none of which exostab models, can decide what happens. No overall verdict is given then.

**How long does a check take?**
About 3–8 seconds for 2–7 planets with the defaults on a recent laptop with many cores, and about 7 s (3 planets)
to 15 s (7 planets) on a single core. The analytic indicators take milliseconds.

**Why are the orbits flat (coplanar)?**
The angles between orbital planes are almost never measured. Transit and radial-velocity inclinations are
measured against the sky, not against each other. The AMD indicator assumes, as Laskar & Petit (2017) do, that
the unknown inclinations carry as much AMD as the eccentricities; strongly inclined systems can carry more.

**Can I trust the result for a billion years?**
No. The integration covers 10,000 orbits of the innermost planet by default (`--orbits` changes this). The AMD
and Hill criteria reach further but make approximations. See [Methods](methods.md).

**Can I install it with `pip install exostab`?**
Not yet: a release on PyPI is planned. Install from GitHub as shown in the [Quickstart](quickstart.md).

**How do I cite exostab?**
Use the repository's `CITATION.cff` and cite the methods and the NASA Exoplanet Archive (see
[Data and assumptions](data-assumptions.md)). A Zenodo DOI will be added with the first archived release.

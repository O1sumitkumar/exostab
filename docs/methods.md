# Methods

This page explains, in plain language, what exostab computes and why. Every formula is written out in the
code docstrings too (`src/exostab/indicators/`), and every choice with its reasons is in
[DECISIONS.md](https://github.com/mimitoz62/exostab/blob/main/DECISIONS.md). References are listed at the end;
full entries are in [`references.bib`](references.bib).

## The question

A planetary system is *dynamically stable* if its planets keep roughly the same orbits for a very long time:
no two planets come close to each other, collide, or throw one another out of the system. Planets pull on each
other gently all the time, and most of the time these tugs average out. But if two planets are too close, or
their orbits too elongated, the tugs can build up until the orbits cross.

Stability cannot be proven for more than two planets. exostab therefore asks the question in three different
ways and reports all three answers.

## Step 1: getting the numbers

Parameters come from the NASA Exoplanet Archive's *Planetary Systems Composite Parameters* table
(`pscomppars`; Christiansen et al. 2025; doi:10.26133/NEA13). The table gives one row per planet, with each
value picked from the best available publication. A row can therefore mix numbers from several papers. The
archive's documentation says so explicitly. Missing values are filled by explicit rules, and every rule that
fires is printed in the report; see [Data assumptions](data-assumptions.md).

All orbits are placed in one plane (*coplanar*), because the tilt between two planets' orbits is almost never
measured. Units are years, astronomical units (AU) and solar masses throughout the integrations.

## Step 2: uncertainties

Every published value has error bars. exostab runs the analysis once for the published ("nominal") values and
then again for many random *draws* within the error bars (20 by default). A result that only holds for the exact
published numbers is not trustworthy. The verdict of each indicator stands only if at least 95% of the draws agree
with the nominal one; otherwise it becomes **marginal**.

## Indicator 1: Hill spacing

Around every planet there is a region, its *Hill sphere*, where the planet's gravity beats the star's tides. Its
radius is about a (m / 3M★)^(1/3), for a planet of mass m at distance a from a star of mass M★. For two planets
one uses the *mutual Hill radius*, R_H = ((m₁ + m₂) / 3M★)^(1/3) (a₁ + a₂)/2, and measures their separation
Δ = (a₂ − a₁)/R_H in these units (Chambers et al. 1996).

**Two planets.** Using a result of Marchal & Bozis (1982) for the three-body problem, Gladman (1993) showed that
two planets on circular orbits can *never* come close to each other if Δ is larger than about 2√3 ≈ 3.46. For
elongated (eccentric) orbits the limit grows. exostab uses the eccentric form of the criterion (as restated by
Veras & Armitage 2004 and Giuppone et al. 2013). Petit, Laskar & Boué (2018) showed that it can be written with the
angular momentum deficit; the two forms agree in exostab's tests.

**Three or more planets.** There is no such proof. Numerical experiments show that the time until the first close
encounter grows roughly exponentially with the spacing Δ (Chambers et al. 1996). Pu & Wu (2015) found that
Kepler-like systems need Δ ≈ 10 to survive a billion years with circular orbits, and Δ ≈ 12 when the eccentricities
are about 0.02. exostab calls a multi-planet system *stable* by this indicator only if every neighbouring pair has
Δ ≥ 12, and *unstable* if any pair fails the two-planet criterion or has crossing orbits.

## Indicator 2: angular momentum deficit (AMD)

The *angular momentum deficit* measures how far a system is from having perfectly circular, flat orbits:

C = Σₖ Λₖ (1 − √(1 − eₖ²) cos iₖ),  with Λₖ = mₖ √(G M★ aₖ)

(Laskar & Petit 2017). Over long times the planets exchange AMD, making one orbit more elongated and another more
circular, but the total stays constant in the orbit-averaged ("secular") dynamics. So the question becomes: is
there enough AMD in the whole system for two neighbouring orbits to become elongated enough to cross? Laskar &
Petit (2017) computed the smallest AMD that allows crossing, the *critical AMD* C_c, for any pair. They defined
β = C / (Λ' C_c), where Λ' belongs to the outer planet of the pair. If β < 1 for every pair, collisions are
impossible in this approximation.

Two refinements:

- Close pairs can become chaotic through overlapping *mean-motion resonances*, where the orbital periods are near
  simple ratios such as 3:2. This happens before their orbits cross. Petit, Laskar & Boué (2017) derived a smaller
  critical AMD for this case, and exostab uses it where it applies. If the planets are so close that resonances
  overlap even for circular orbits, β is infinite.
- For two planets, Petit, Laskar & Boué (2018) wrote the Hill criterion in AMD form. exostab uses it to tell
  "AMD-unstable but Hill stable" (marginal) from "neither" (unstable).

AMD instability does not mean the system will fall apart. The Solar System itself is AMD-unstable, because Mercury
could in principle collide with Venus (Laskar & Petit 2017). It means only that AMD conservation cannot rule
collisions out.

## Indicator 3: direct N-body integration and MEGNO

The most direct test is to compute the orbits forward in time. exostab uses REBOUND (Rein & Liu 2012) with WHFast
(Rein & Tamayo 2015), a fast *symplectic* integrator. Symplectic integrators keep the energy error bounded, so
they can run for very long times. The time step is 1/30 of the time the most eccentric planet takes to swing
through its closest approach to the star. Wisdom (2015) found 1/20 of that time adequate (as restated by Hadden &
Lithwick 2018). The same run is repeated with IAS15 (Rein & Spiegel 2015), an adaptive high-accuracy integrator,
as a check.

Surviving is not enough, because a chaotic system can survive for a while and then fall apart. exostab therefore
also computes the chaos indicator **MEGNO**, ⟨Y⟩ (Cincotta & Simó 2000; Cincotta, Giordano & Simó 2003), from
REBOUND's variational equations (Rein & Tamayo 2016). MEGNO tracks how fast two infinitely close copies of the
system drift apart. For regular (quasi-periodic) motion ⟨Y⟩ settles at 2; for chaotic motion it keeps growing.
exostab counts ⟨Y⟩ ≥ 2.2 as chaotic. This threshold is a judgment call: published choices range from
|⟨Y⟩ − 2| ≤ 0.001 for very long runs to ⟨Y⟩ ≳ 5 (DECISIONS.md, D8).

Each run is classified as:

- **regular**: no close encounter or escape, and ⟨Y⟩ < 2.2;
- **chaotic**: no close encounter or escape, but ⟨Y⟩ ≥ 2.2;
- **unstable**: two planets came closer than the mean of their Hill radii, or a planet moved beyond 100 times
  the largest orbit;
- **inconclusive**: the relative energy error exceeded 10⁻⁵, so the numbers cannot be trusted.

By default each run lasts 10,000 orbits of the innermost planet. That is a short time compared with the age of a
planetary system, and exostab never claims more than "no instability found within this time".

## Step 3: the overall verdict

- **unstable**: the direct integration shows close encounters or escapes for the published values and for almost
  all draws;
- **inconclusive**: the integrations could not be trusted;
- **stable**: all three indicators say stable;
- **marginal**: everything else, in particular whenever the indicators disagree.

A typical *marginal* case is a system in a resonance, such as GJ 876: the analytic criteria fail, but the
integration shows regular motion. The report explains which indicators disagree and why.

## References

- Chambers, J. E., Wetherill, G. W. & Boss, A. P. 1996, Icarus 119, 261, doi:10.1006/icar.1996.0019
- Christiansen, J. L., et al. 2025, PSJ 6, 186, doi:10.3847/psj/ade3c2
- Cincotta, P. M. & Simó, C. 2000, A&AS 147, 205, doi:10.1051/aas:2000108
- Cincotta, P. M., Giordano, C. M. & Simó, C. 2003, Physica D 182, 151, doi:10.1016/s0167-2789(03)00103-9
- Giuppone, C. A., Morais, M. H. M. & Correia, A. C. M. 2013, MNRAS 436, 3547, doi:10.1093/mnras/stt1831
- Gladman, B. 1993, Icarus 106, 247, doi:10.1006/icar.1993.1169
- Hadden, S. & Lithwick, Y. 2018, AJ 156, 95, doi:10.3847/1538-3881/aad32c
- Laskar, J. & Petit, A. C. 2017, A&A 605, A72, doi:10.1051/0004-6361/201630022
- Marchal, C. & Bozis, G. 1982, Celestial Mechanics 26, 311, doi:10.1007/bf01230725
- Petit, A. C., Laskar, J. & Boué, G. 2017, A&A 607, A35, doi:10.1051/0004-6361/201731196
- Petit, A. C., Laskar, J. & Boué, G. 2018, A&A 617, A93, doi:10.1051/0004-6361/201833088
- Pu, B. & Wu, Y. 2015, ApJ 807, 44, doi:10.1088/0004-637x/807/1/44 (erratum ApJ 819, 170)
- Rein, H. & Liu, S.-F. 2012, A&A 537, A128, doi:10.1051/0004-6361/201118085
- Rein, H. & Spiegel, D. S. 2015, MNRAS 446, 1424, doi:10.1093/mnras/stu2164
- Rein, H. & Tamayo, D. 2015, MNRAS 452, 376, doi:10.1093/mnras/stv1257
- Rein, H. & Tamayo, D. 2016, MNRAS 459, 2275, doi:10.1093/mnras/stw644
- Veras, D. & Armitage, P. J. 2004, Icarus 172, 349, doi:10.1016/j.icarus.2004.06.012
- Wisdom, J. 2015, AJ 150, 127, doi:10.1088/0004-6256/150/4/127

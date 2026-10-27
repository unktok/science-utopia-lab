# NOCTILUCA // Research Arcology — Art Bible v0.1

Status: creative preproduction. This document defines the target for the next
game-quality vertical slice; the current browser UI remains an audit prototype.

## Creative thesis

The scientific system is a city. Knowledge glows, institutions cast shadows,
and every visible scientific flow can be traced to evidence. The tone combines
intellectual excitement, solidarity, competition, repair, and institutional
opacity. Cyberpunk is expressed through the politics and infrastructure of the
world—not by adding purple glow to a dashboard.

The game view must dominate 70–80% of the screen. Researchers inhabit the
world, institutions have distinct silhouettes and interiors, and papers,
reviews, citations, funding, data, and policy move through the city. The player
can travel from the city view to the canonical event that supports a visual.

The generated concept at
[`art/concepts/noctiluca-keyframe-v0.png`](art/concepts/noctiluca-keyframe-v0.png)
is a visual target for density, institutional variety, and visible flows. It is
not a production sprite sheet and must not be shipped as one.

## Pixel specification

| Property | Rule |
|---|---|
| Logical canvas | 480×270, 16:9 |
| Display scale | integer only; 3× gives 1440×810 |
| Tile grid | 16×16 px |
| Researcher | 24×32 px; foot anchor `(12, 28)` |
| Portrait | 64×64 px |
| Flow packet | 8×8 px; effect envelope 16×16 or 24×24 px |
| Rendering | nearest-neighbor; no subpixel positioning or smoothing |
| Outline | 1 px deep indigo exterior; local shadow for internal lines |
| Light | upper-left ambient light; lower-right institutional neon bounce |
| Material shading | 3–4 values per material |

Dithering is reserved for skies, fog, and very large surfaces. Characters,
icons, evidence marks, and flow packets must remain crisp at 1×.

## Master palette

The initial 24-color palette is fixed until the art-quality vertical slice is
reviewed. A sprite should normally use 8–12 colors.

```text
dark       #070814 #10142A #1A2140 #2A3560
interface  #46527A #6A769A #9EA8C2 #EEE9D8
neon       #39F5C8 #2DD4FF #4F7CFF #A86BFF
accent     #F653D8 #FF617D #FFC857 #B7F34A
material-a #382330 #704154 #A85F62 #D88E70
material-b #F1BD91 #F7DEC0 #6E4C2E #B07A44
```

Meaning must never depend on hue alone. Silhouette, icon, line pattern, and
motion distinguish semantic classes.

## World districts

- **University Arcology:** linked teaching and research towers, old stone,
  patched conduits, rooftop gardens, instrument exhaust.
- **Laboratory Quarter:** wet labs, field stations, compute vaults, fabrication
  bays, data stewardship rooms.
- **Public Knowledge Commons:** library, archive, open-data nodes, citizen
  access, informal collaboration.
- **Peer Review Exchange:** anonymous review chambers, editorial routing,
  visible queues and overload.
- **Publication Spine:** preprint bazaar, publishing tower, repository servers,
  citation observatory.
- **Funding Authority:** ledger vault, application intake, allocation ports,
  resource dispatch.
- **Government Observatory:** public deliberation, policy transmission,
  inspection and appeal.
- **Conference Forum:** talks, posters, encounters, disciplinary crossings.

No building may be a recolored generic rectangle. Each type must be readable
from silhouette alone and expose at least one state-dependent activity layer.

## Researchers

Characters are assembled from body, head, hair, clothing, tool, mobility aid,
and emissive accessory layers. Role must not be fixed to gender, skin tone, age,
or disability.

Initial roles: early-career researcher, principal investigator, theoretician,
experimentalist, field researcher, computational researcher, technician, data
steward, librarian/archivist, reviewer/editor, funder, and science-policy
official.

Initial animation vocabulary:

| State | Frames | Rate |
|---|---:|---:|
| idle | 4 | 4 fps |
| walk, four directions | 6 each | 8 fps |
| terminal work / experiment | 8 | 6 fps |
| read / write / review | 6 each | 5–8 fps |
| talk / collaborate / present | 8 each | 6–8 fps |
| handoff | 6 | 10 fps |
| exit | 8 | 6 fps |

Do not infer emotions from resource state or rejection. Show an emotion only
when the simulator supplies a corresponding state. Otherwise show observable
actions such as inactivity, queueing, departure, or a stopped terminal.

## Flow grammar

| Flow | Shape and motion | World meaning |
|---|---|---|
| Data | cyan segmented cell train | lab, collaborator, repository |
| Paper | ivory folded-page carrier | author, venue, archive |
| Review | magenta eye/seal shard | venue, reviewer, editor |
| Funding | mint hexagonal credit pulse | authority, institution, researcher |
| Citation | violet bracket and one-shot arc | paper-to-paper knowledge link |
| Policy | coral stamped document and broadcast wave | governance-to-mechanism change |

Canonical flows use a solid path and link to event IDs. Derived choreography
uses a dashed path and records its derivation. Ambient traffic is visually
subdued and explicitly labeled `AMBIENT`. Dense flows aggregate into a band
with a count rather than producing unbounded particles.

## Evidence contract

Every scientific visual has one truth status:

- `canonical`: directly represented by one or more replay events;
- `derived`: deterministically computed from canonical events with a recorded
  derivation version;
- `ambient`: atmospheric motion that makes no scientific claim.

The next replay schema should attach `derived_from_event_ids`,
`derivation_version`, and `truth_status` to choreography. Native simulator
events are required before the UI claims to show question formation, writing,
collaboration, citation, funding applications, publication, or government
action. A hash supplied by the payload is not “verified” until the client
recomputes and compares it.

## Camera and information hierarchy

- LOD 0: city silhouettes, crowds, bundled flows, no small labels.
- LOD 1: individual researchers, packets, main institutions.
- LOD 2: interior cutaways, desks, instruments, current actions.
- LOD 3: portrait, career and resource ledger, papers, decisions, provenance.

The viewport supports pan, integer zoom, follow-agent, minimap, and layer
filters. The top bar contains run/branch/year/phase/verification state; the
bottom contains playback and event lanes; left and right inspectors open only
when needed. Metrics are overlays, not permanent dashboard cards.

## Accessibility and atmosphere

Maintain a semantic DOM mirror of the canvas state so every entity and event is
keyboard and screen-reader reachable. Critical distinctions use shape and text
in addition to color. Support reduced motion, high contrast, 200% UI zoom, and
an atmosphere intensity control. Rain, CRT effects, chromatic separation, and
glitch are optional; they must never obscure evidence or flash rapidly.

## Asset naming and atlas rules

```text
su_<family>_<subject>_<variant>_<state>_<direction>_f<frame>_lod<level>.png
```

Do not rotate packed sprites. Use 2 px padding and 1 px edge extrusion. The
manifest records pivot, collision shape, fps, loop mode, event tags, semantic
ID, palette version, source revision, authoring source, provenance, and license.

## Quality gate

Generated images may support composition, silhouette, architecture, and palette
exploration. Production sprites must be redrawn on the fixed grid. A release
candidate requires:

- zero out-of-palette colors and zero antialiased edge pixels;
- silhouette recognition at 1×;
- pivot drift no greater than 1 px across a cycle;
- flow types distinguishable without color;
- deterministic screenshot at the same replay, cursor, camera, and viewport;
- no scientific motion without a canonical or derived evidence link;
- reduced-motion and representative still frames for every animation;
- art, science-domain, and accessibility review.

## First art-quality vertical slice

Build one 30–60 second causal sequence before scaling asset production:

1. three distinct researchers work in a laboratory;
2. a data flow produces a paper submission;
3. the paper travels to the review exchange and two reviewers act;
4. a review returns, revision occurs, and the paper is published;
5. a citation pulse reaches a second laboratory;
6. a funding pulse visibly changes laboratory capacity.

The slice uses three institutions, all six flow types, four world states
(normal, overloaded, underfunded, publication), and dawn/day/dusk/night
atmosphere. Every scientific action must click through to its evidence.

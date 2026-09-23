# Helsinki Service Map entrance evidence

This bounded WP1/WP2 audit adds an **independent source for service-unit identity and published entrance points**. It does not replace the HSL/OSM CityPack, choose a directed road junction, or validate vehicle access. The frozen [source snapshot](../evidence/wp1/service_map_entrance_source_snapshot.json) records exact official URLs, UTC retrieval times, full-response SHA256 hashes, and projected public fields. It **does not contain complete raw API responses**; a hash and projection support provenance, but cannot reproduce removed fields without re-querying the source. The [derived audit](../evidence/wp1/service_map_entrance_audit.json) is reproducible offline from that projection.

The City of Helsinki Service Map [REST v4 API](https://www.hel.fi/palvelukarttaws/restpages/ver4_en.html) publishes service units and entrance records. Its [terms](https://www.hel.fi/palvelukarttaws/restpages/index_en.html) permit reuse under **CC BY 4.0** with attribution to **City of Helsinki Service Map**. The provider does not guarantee correctness. No photographs are copied. OSM facility geometry remains © OpenStreetMap contributors, ODbL 1.0, distributed through HSL. The Service Map snapshot was retrieved on 2026-09-23 UTC; it does not establish facility state during the May 2026 historical events.

| Frozen OSM facility way | Official evidence | Identity decision | Directed road access |
| --- | --- | --- | --- |
| `1076884314`, unnamed `school` | No school among eight published units within 300 m of the anchor; original road snap exceeds 300 m. | Unresolved; an amenity tag alone is not an identity. | Not verified. |
| `1100772558`, Tölö gymnasium | Exact-name school unit `6820`, Sandelsinkatu 3, 15.51 m from the OSM anchor; official main entrance `19489` at `24.921834224, 60.179212613`. | Candidate source-backed **unit identity** only. | Not verified; neither candidate road node is promoted. |
| `33538166`, Kivelän sairaala | Exact-name search finds no current hospital unit. Nearby Kivelä units include health care and senior services with different entrance IDs. | Unresolved historical/site identity. | Not verified. |
| `33323000`, Auroran sairaala | The large OSM hospital site contains several official service units/buildings; psychiatry unit `26110` has entrance `21577`. | Unresolved site-to-unit correspondence. | Not verified. |
| `39343294`, Stadin ammattiopisto Sturenkatu | Original exact-name search returns no unit; same-address sports-hall unit `41077` has entrance `22849`. | Unresolved school-to-sports-hall correspondence. | Not verified. |

The official `entrance/` collection includes `unit_id`, coordinates and `is_main_entrance`. Its `?unit=` parameter did not filter the response when inspected; this audit therefore pins **seven known entrance IDs** and refreshes each single-record endpoint. It is not a complete inventory of entrances. An official building entrance can be a pedestrian or service-unit point and may sit inside an OSM amenity polygon. Proximity to a passenger-road junction does not show a usable driveway, permitted direction or turn, emergency-vehicle exemption, or historical opening time.

Run the reproducible offline check without network access:

```sh
PYTHONPATH=core:. uv run --frozen python scripts/service_map_entrances.py
PYTHONPATH=core:. uv run --frozen python -m pytest -q test_suite/data/test_service_map_entrances.py
```

Refresh only the fixed public unit searches and seven direct entrance records, with explicit egress permission and no model calls:

```sh
PYTHONPATH=core:. uv run --frozen python scripts/service_map_entrances.py --refresh --allow-egress
```

Review the refreshed diff and changed source timestamps before committing. A refresh reads the **current** municipal source and can change independently of the frozen OSM bytes; it is not a historical reconstruction. The adapter requires a unique exact multilingual name and a unit point within 100 m of the OSM facility anchor to label an **identity candidate**; this is a conservative filter, not proof of entrance geometry. A separate source-backed pedestrian/vehicle access path and directed-road permission/turn check, followed by human review for ambiguous sites, is still required before `G102` or full-coverage `G205` can pass. The current 48-target boundary case remains scoped to its frozen candidate entrances.

## Offline directed-road candidate queue

The [derived road candidate report](../evidence/wp1/service_map_road_candidates.json) compares the seven **inspected** official entrance points with the local, current-network Helsinki CityPack. It keeps the five OSM facility anchors and all seven inspected Service Map entrance records, including entrance records for units whose correspondence to the OSM facility is unresolved. The report therefore does **not** claim seven confirmed facility entrances. The unnamed school has no inspected official entrance point and receives no road candidate.

Distances are from each entrance point to the closest point on each directed edge geometry, projected to Finland's EPSG:3067 metric CRS. The five nearest directed edges are listed in stable distance/ID order. **Separately**, the report includes the nearest edge whose imported permissions allow a passenger car and the nearest whose imported permissions allow an emergency vehicle, even if either falls outside the closest five; a missing class candidate is `null`. Every candidate has a 150 m review-radius flag, imported vehicle classes, modeled turn coverage/counts, source IDs and hashes. Edges outside the radius are still listed as nearest candidates; the radius is a reviewer aid, not an access threshold. If the CityPack has no connection list, turn coverage is explicitly unknown and turn counts are `null` rather than zero. A present list records imported model turns, not independently verified completeness. The CityPack is read only, and no edge, facility entrance, or permission is changed. The input SHA256 hashes pin the exact frozen source projection and local CityPack bytes used for this report; the CityPack itself remains in the ignored deployer data directory.

For example, Tölö gymnasium's official entrance `19489` is 35.22 m from its nearest directed road edge in the current CityPack, while Aurora unit entrance `21577` is 1.45 m from an edge whose imported classes include delivery, bicycle and pedestrian but **not passenger or emergency**. Aurora's nearest imported passenger/emergency-permitted edge is instead 52.66 m away. These values are geometric candidates only. They do not establish a driveway, permitted passage from the building, current operational access, or May 2026 event-time access. An imported turn count only describes the modeled edge-to-edge network, not a turn from the building into that road.

Rebuild this report offline after obtaining the local Helsinki CityPack:

```sh
PYTHONPATH=core:. uv run --frozen python scripts/service_map_road_candidates.py \
  --citypack /absolute/path/to/data/citypacks/helsinki-current/citypack.json
PYTHONPATH=core:. uv run --frozen pytest -q test_suite/data/test_service_map_road_candidates.py
```

The command requires the CityPack path explicitly and makes no network or model calls. The saved report remains `CANDIDATES_ONLY_NOT_VERIFIED`; G102 and G205 remain `PARTIAL`. A reviewer still needs a source-backed unit/site correspondence, an actual building-to-road access path, directed road permissions and event-time applicability before promoting any connection.

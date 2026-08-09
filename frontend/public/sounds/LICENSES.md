# Soundboard audio — sources & licenses

All five sounds are free for commercial use without attribution. Each file was
loudness-normalized (loudnorm I=-16 LUFS) and encoded to MP3 112 kbps.

| File              | Sound                                                                       | Source                                                     | License                                                                 |
| ----------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------- |
| `applause.mp3`    | "Animated small group applause" (Mixkit sfx 523)                            | <https://mixkit.co/free-sound-effects/applause/>           | [Mixkit Sound Effects Free License](https://mixkit.co/license/#sfxFree) |
| `boo.mp3`         | "Voice_Crowd_Small_Expression_Boo_Stereo" by Nox_Sound                      | <https://freesound.org/people/Nox_Sound/sounds/752707/>    | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)           |
| `drumroll.mp3`    | "Drum Roll" (Mixkit sfx 566), trimmed to the final 4 s (cymbal ending kept) | <https://mixkit.co/free-sound-effects/drum/>               | [Mixkit Sound Effects Free License](https://mixkit.co/license/#sfxFree) |
| `buzzer.mp3`      | "Game show wrong answer buzz" (Mixkit sfx 950)                              | <https://mixkit.co/free-sound-effects/buzzer/>             | [Mixkit Sound Effects Free License](https://mixkit.co/license/#sfxFree) |
| `airhorn.mp3`     | "DJ airhorn sound" by pfranzen                                              | <https://freesound.org/people/pfranzen/sounds/528807/>     | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)           |
| `laugh.mp3`       | "Crowd laugh" (Mixkit sfx 424)                                              | <https://mixkit.co/free-sound-effects/laugh/>              | [Mixkit Sound Effects Free License](https://mixkit.co/license/#sfxFree) |
| `sadtrombone.mp3` | "wah wah sad trombone" by kirbydx                                           | <https://freesound.org/people/kirbydx/sounds/175409/>      | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)           |
| `crickets.mp3`    | "synth-cricket" by guitarguy1985                                            | <https://freesound.org/people/guitarguy1985/sounds/69439/> | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)           |
| `tada.mp3`        | "Tada Fanfare A" by plasterbrain                                            | <https://freesound.org/people/plasterbrain/sounds/397355/> | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)           |

The file ids must stay in sync with the backend allowlist
(`backend/app/sockets/payloads.py`, `AllowedSound`) and the frontend list in
`frontend/src/components/Soundboard.vue`.

document.addEventListener('DOMContentLoaded', () => {

    const translations = {
        pageTitle: {
            sk: '3D Pero – Projekt',
            en: '3D Pen – Project',
        },
        logoText: {
            sk: '3D Pero',
            en: '3D Pen',
        },
        navGallery: {
            sk: 'Galéria',
            en: 'Gallery',
        },
        navTutorials: {
            sk: 'Návody',
            en: 'Tutorials',
        },
        navBlueprints: {
            sk: 'Šablóny',
            en: 'Blueprints',
        },
        navInfo: {
            sk: 'Info',
            en: 'Info',
        },
        translateButton: {
            sk: 'EN',
            en: 'SK',
        },

        introText: {
            sk: 'Táto platforma prináša didaktické materiály pre prácu s 3D perom v geometrii:',
            en: 'This platform provides didactic materials for working with a 3D pen in geometry:',
        },
        introItem1: {
            sk: '<strong>Voľné rovnobežné premietanie</strong><br />Sada úloh a šablón na modelovanie základných telies a ich premietov, ktorá zlepšuje vizuálnu názornosť priestorových vzťahov priestor‐rovina.',
            en: '<strong>Free Parallel Projection</strong><br />A set of exercises and templates for modeling basic solids and their projections, which enhances visual understanding of space‐plane relationships.',
        },
        introItem1Strong: {
            sk: 'Voľné rovnobežné premietanie',
            en: 'Free Parallel Projection',
        },
        introItem2: {
            sk: '<strong>Metrické úlohy v stereometrii</strong><br />Príklady polohových vzťahov, výpočty uhlov a vzdialeností s 3D perom vrátane hodnotenia cenovo dostupných per a ekologických filamentov.',
            en: '<strong>Metric Exercises in Stereometry</strong><br />Examples of positional relationships, angle and distance calculations using a 3D pen, including an assessment of affordable pens and eco-friendly filaments.',
        },
        introItem2Strong: {
            sk: 'Metrické úlohy v stereometrii',
            en: 'Metric Exercises in Stereometry',
        },
        introItem3: {
            sk: '<strong>Rovinné rezy priestorových telies</strong><br />Manuál a šablóny na tvorbu rezov kociek, vysvetlenie rôznych polôh rezových rovin a prehľad vhodných 3D pier do škôl.',
            en: '<strong>Planar Sections of 3D Solids</strong><br />Manual and templates for making cuts of cubes, explanations of different section planes, and an overview of suitable 3D pens for schools.',
        },
        introItem3Strong: {
            sk: 'Rovinné rezy priestorových telies',
            en: 'Planar Sections of 3D Solids',
        },

        heroTitle: {
            sk: 'Preskúmaj ukážky 3D látok vytvorených pomocou 3D pera',
            en: 'Explore 3D Objects Created with a 3D Pen',
        },
        heroSubtitle: {
            sk: 'Zisti čo všetko 3D pero dokáže a nechaj sa inšpirovať!',
            en: 'Discover everything a 3D pen can do-and let yourself be inspired!',
        },
        openGalleryButton: {
            sk: 'POZRI GALÉRIU',
            en: 'VIEW GALLERY',
        },

        tutorial1: {
            sk: 'Návod 1',
            en: 'Tutorial 1',
        },

        blueprintsTitle: {
            sk: 'Šablóny',
            en: 'Blueprints',
        },
        blueprint1Title: {
            sk: 'Šablóny pre voľné rovnobežné premietanie',
            en: 'Templates for Free Parallel Projection',
        },
        blueprint1Desc: {
            sk: 'Interaktívny didaktický materiál s úlohami a presnými šablónami pre tvorbu modelov základných telies a ich premietov, ktorý pomáha učiteľom aj žiakom lepšie pochopiť vzťahy medzi 3D objektmi a ich projekciami do roviny.',
            en: 'Interactive didactic materials with exercises and precise templates for building models of basic solids and their projections, helping teachers and students better understand the relationships between 3D objects and their 2D projections.',
        },
        blueprint1Button: {
            sk: 'Stiahni PDF',
            en: 'Download PDF',
        },
        blueprint2Title: {
            sk: 'Šablóny pre metrické úlohy v stereometrii',
            en: 'Templates for Metric Exercises in Stereometry',
        },
        blueprint2Desc: {
            sk: 'Sada príkladov ilustrujúcich polohové vzťahy priamok a rovín, výpočty uhlov a vzdialeností s využitím 3D pera, papierového pravítka a premietacieho kútika. Práca tiež hodnotí cenovo dostupné perá a ekologické filamenty.',
            en: 'A set of examples illustrating positional relationships of lines and planes, angle and distance calculations using a 3D pen, paper ruler, and projection corner. The work also evaluates affordable pens and eco-friendly filaments.',
        },
        blueprint2Button: {
            sk: 'Stiahni PDF',
            en: 'Download PDF',
        },
        blueprint3Title: {
            sk: 'Šablóny pre rovinné rezy priestorových telies',
            en: 'Templates for Planar Sections of 3D Solids',
        },
        blueprint3Desc: {
            sk: 'Manuál k šablónam na konštrukciu rezov kociek rôznymi rovinami – obsahuje návod a šablóny pre 3D pero aj prehľad vhodných modelovacích materiálov.',
            en: 'Manual for templates to construct cuts of cubes by different planes—includes instructions and templates for the 3D pen as well as an overview of suitable modeling materials.',
        },
        blueprint3Button: {
            sk: 'Stiahni PDF',
            en: 'Download PDF',
        },

        infoTitle: {
            sk: 'Dôležité informácie o 3D perách a stereometrii',
            en: 'Important Information about 3D Pens and Stereometry',
        },
        info1Title: {
            sk: '1. Priestorová geometria a inovatívne prístupy',
            en: '1. Spatial Geometry and Innovative Approaches',
        },
        info1Para1: {
            sk: `Učiť sa priestorové vzťahy neznamená len čmárať tvary na papier.
Žiaci si môžu postaviť jednoduché telesá (kocky, ihlany, hranoly)
pomocou 3D pera a priamo vidia, ako sa zmení tvar pri premietaní do
dvojrozmernej roviny. Tento „dotykový“ prístup podporuje hlbšie
pochopenie a rýchlejšie zapamätanie, pretože priestor nie je
abstrakciou, ale hmatateľnou realitou.`,
            en: `Learning spatial relationships isn’t just about drawing shapes on paper.
Students can build simple solids (cubes, pyramids, prisms) with a 3D pen and see
directly how those shapes change when projected onto a 2D plane. This “hands‐on”
approach fosters deeper understanding and faster retention because space becomes
tangible, not abstract.`,
        },
        info2Title: {
            sk: '2. Čo je 3D pero, aké filamenty a ako ich využiť',
            en: '2. What a 3D Pen Is, Which Filaments to Use, and How to Use Them',
        },
        info2Para1: {
            sk: `3D pero je vlastne malá 3D tlačiareň v rukách – zahrieva ekologický
PLA filament na približne 200 °C a vytvára vrstvy plastu. Pre školy sa
hodia lacnejšie, no spoľahlivé PLA filamente (nielen z ekonomického,
ale aj z ekologického hľadiska). K práci potrebujete:`,
            en: `A 3D pen is essentially a small handheld 3D printer—it heats eco‐friendly
PLA filament to about 200 °C and deposits plastic layer by layer. For schools,
inexpensive yet sturdy PLA filaments are ideal (not only for budgetary but also
environmental reasons). You’ll need:`,
        },
        info2List: {
            sk: `<ul>
  <li>pevná podložka (napr. PVC), nech sa filament nelepí na lavice,</li>
  <li>náhradná tryska a pár gramov PLA, čo postačuje pre desiatky modelov,</li>
  <li>náhradné 3D pero, aby hodina neostala „zamrznutá“, keď jedno pero zhasne.</li>
</ul>`,
            en: `<ul>
  <li>a sturdy work surface (e.g., PVC) so the filament won’t stick to desks,</li>
  <li>a spare nozzle and a few grams of PLA (enough for dozens of models),</li>
  <li>a backup 3D pen so the lesson doesn’t stall if one pen runs out of filament.</li>
</ul>`,
        },
        info3Title: {
            sk: '3. Návrh úloh zo stereometrii s 3D perom',
            en: '3. Designing Stereometry Exercises with a 3D Pen',
        },
        info3Strong1: {
            sk: 'Metrické vzťahy:',
            en: 'Metric Relationships:',
        },
        info3Para1: {
            sk: `Namiesto papierových vzorcov postavíte dve
mimobežné priamky či priamku a rovinu. 3D pero vám pomôže vytvoriť kolmú stenu
alebo pás medzi nimi tak, aby ste hmatom merali pravý uhol alebo vzdialenosť.`,
            en: `Instead of paper‐and‐pencil formulas, you’ll build two skew lines or a line and a plane.
The 3D pen helps you create a perpendicular wall or strip between them so you can physically
measure the right angle or distance by touch.`,
        },
        info3Strong2: {
            sk: 'Rezy kocky:',
            en: 'Cube Sections:',
        },
        info3Para2: {
            sk: `Sestavíte jednoduchú kocku z pár vrstiev filamentu,
vyznačíte tri body a pomocou 3D pera urobíte rez. Výsledný päťuholník či šesťuholník
vidíte priamo, nie len v mysli.`,
            en: `You’ll build a simple cube out of a few filament layers, mark three points, and
use the 3D pen to make the cut. You see the resulting pentagon or hexagon physically,
not just in your imagination.`,
        },
        info3Strong3: {
            sk: 'Voľné rovnobežné premietanie:',
            en: 'Free Parallel Projection:',
        },
        info3Para3: {
            sk: `Modelujte kváder pod 45 °C uhol a porovnajte, ako sa rovnobežné čiary menia pri rôznych
uhloch pohľadu. Tým pochopíte, prečo uhol medzi telesom a rovinou skracuje kolmé úsečky.`,
            en: `Model a prism at a 45° angle and compare how parallel lines change at different viewing angles.
This shows you why the angle between a solid and a plane shortens perpendicular segments.`,
        },
        info4Title: {
            sk: '4. Pre učiteľov – realizácia v triede',
            en: '4. For Teachers – Classroom Implementation',
        },
        info4Strong1: {
            sk: 'Organizácia:',
            en: 'Organization:',
        },
        info4Para1: {
            sk: `Rozdeľte triedu do skupín po 3 – 4 žiakoch, aby
každá skupina mala aspoň jedno pero. Pred začiatkom ukažte hotový model (rez
kocky alebo kvádra pod uhlom) a vysvetlite, čo žiaci dosiahnu.`,
            en: `Divide the class into groups of 3–4 students so each group has at least one pen.
Before starting, show a completed model (a cube or prism cut at an angle) and explain what
students will achieve.`,
        },
        info4Strong2: {
            sk: 'Pomôcky:',
            en: 'Materials:',
        },
        info4Para2: {
            sk: `PVC podložky, aby sa zatvrdnutý filament nelepil na stoly,
a náhradné trysky (pendrive s videom, ako sa vkladá filament, pomôže znížiť čas,
ktorý žiaci strávia nastavovaním pera).`,
            en: `PVC mats so hardened filament won’t stick to desks, and spare nozzles (a USB with
a short video on how to load filament saves students setup time).`,
        },
        info4Strong3: {
            sk: 'Priebeh hodiny:',
            en: 'Lesson Flow:',
        },
        info4Para3: {
            sk: `Žiaci najprv zostavia základné tvary – obrysy kocky či ihlanu.
Keď vidia, ako sa vrstvy ukladajú, má učiteľ priestor na diskusiu a vysvetlenie teórie.
Čas, ktorý by sa inak strávil kreslením, sa využíva na praktické modelovanie.`,
            en: `Students first build basic shapes—outlines of a cube or pyramid. As they watch the layers
form, the teacher can discuss and explain the theory. Time that would’ve been spent drawing
is now used for hands‐on modeling.`,
        },
        info5Title: {
            sk: '5. Vyhodnotenie experimentálneho vyučovania',
            en: '5. Evaluation of Experimental Teaching',
        },
        info5Para1: {
            sk: `Po pilotnom experimente so 3D perom testy na priestorovú predstavivosť ukázali, že
žiaci dosiahli omnoho presnejšie výsledky a rýchlejšie riešili úlohy (v priemere o
niekoľko minút oproti papierovej skupine).`,
            en: `After the pilot with the 3D pen, spatial imagination tests showed that students got much
more accurate results and solved tasks faster (on average several minutes faster than the
paper‐only group).`,
        },
        info5Para2: {
            sk: `Kvalitatívne spätné väzby potvrdili, že práce s perom sú zábavnejšie a kolektivita v
triede sa zlepšila. Experimentálna výučba tak priniesla:`,
            en: `Qualitative feedback confirmed that working with the pen was more fun, and teamwork
in the class improved. Experimental teaching yielded:`,
        },
        info5List: {
            sk: `<ul>
  <li>lepšiu angažovanosť,</li>
  <li>zvýšenú presnosť pri meraní,</li>
  <li>rýchlejšie zvládnutie úloh,</li>
  <li>zdravú konkurenciu a tímovú spoluprácu.</li>
</ul>`,
            en: `<ul>
  <li>better engagement,</li>
  <li>increased measurement accuracy,</li>
  <li>faster task completion,</li>
  <li>healthy competition and team collaboration.</li>
</ul>`,
        },
        info5Para3: {
            sk: `Jedno 3D pero stojí približne 30 € a jeden kilogram gutenomer PLA filamentov (okolo
330 m filamentu) stojí cca 25 €. Priemerne 10 g filamentu postačí na jednu úlohu
za hodinu pre 3 žiakov – takže jeden kilogram vystačí pre stovky žiakov, čo je
rozpočtovo prijateľné.`,
            en: `One 3D pen costs about €30, and one kilogram of PLA filament (around 330 m) costs
about €25. On average, 10 g of filament covers one hour’s task for three students—so
one kilogram suffices for hundreds of students, which is budget‐friendly.`,
        },

        galleryPhotos: {
            sk: 'Fotky',
            en: 'Photos',
        },
        galleryVideos: {
            sk: 'Videá',
            en: 'Videos',
        },

        footerText: {
            sk: '© 2026 I. Novikov 3Ain',
            en: '© 2026 I. Novikov 3Ain',
        },
    };

    let currentLang = 'sk';

    function applyTranslations() {
        document
            .querySelectorAll('[data-i18n-key]')
            .forEach((elem) => {
                const key = elem.getAttribute('data-i18n-key');
                if (!translations[key]) return;

                const val = translations[key][currentLang];

                if (val.includes('<')) {
                    elem.innerHTML = val;
                } else {
                    elem.innerText = val;
                }
            });
    }

    function toggleTranslation() {
        currentLang = currentLang === 'sk' ? 'en' : 'sk';
        applyTranslations();
    }

    applyTranslations();

    const vidObserver2 = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            const video = entry.target;
            if (entry.isIntersecting) {
                video.muted = true;
                video.play().catch(() => {});
            } else {
                video.pause();
            }
        });
    }, { threshold: 0.5 });
    document.querySelectorAll('.bg-video').forEach(v => vidObserver2.observe(v));

    const openGalleryBtn = document.getElementById('open-gallery');
    const galleryModal   = document.getElementById('gallery-modal');
    const galleryClose   = document.getElementById('gallery-close');
    const galleryOverlay = document.querySelector('.gallery-modal-overlay');

    function disablePageScroll() {
        document.body.style.overflow = 'hidden';
    }
    function enablePageScroll() {
        document.body.style.overflow = '';
    }

    if (openGalleryBtn && galleryModal && galleryClose && galleryOverlay) {
        openGalleryBtn.addEventListener('click', (e) => {
            e.preventDefault();
            galleryModal.classList.remove('hidden');
            disablePageScroll();
        });
        [galleryClose, galleryOverlay].forEach(el => {
            el.addEventListener('click', () => {
                galleryModal.classList.add('hidden');
                enablePageScroll();
            });
        });
    }

    function filterGallery(rawQuery) {
        const q = rawQuery.trim().toLowerCase();

        document.querySelectorAll('.gallery-thumb.photo-thumb').forEach(thumb => {
            const img = thumb.querySelector('img');
            const titleText = img && img.alt ? img.alt.toLowerCase() : '';
            const keywordsText = thumb.dataset.keywords ? thumb.dataset.keywords.toLowerCase() : '';
            thumb.style.display = (titleText + ' ' + keywordsText).includes(q) ? '' : 'none';
        });

        document.querySelectorAll('.gallery-thumb.video-thumb').forEach(thumb => {
            const hdr = thumb.querySelector('.video-overlay h3');
            const titleText = hdr ? hdr.textContent.toLowerCase() : '';
            const keywordsText = thumb.dataset.keywords ? thumb.dataset.keywords.toLowerCase() : '';
            thumb.style.display = (titleText + ' ' + keywordsText).includes(q) ? '' : 'none';
        });
    }

    const searchInput2 = document.getElementById('gallery-search');
    if (searchInput2) {
        searchInput2.addEventListener('input', () => {
            filterGallery(searchInput2.value);
        });
    }

    (function() {
        const slider = document.querySelector('.hero__slider');
        const dots   = Array.from(document.querySelectorAll('.hero__dots .dot'));
        const total  = dots.length;
        let current  = 0;
        let timer;

        if (!slider || dots.length === 0) return;

        function goTo(idx) {
            current = (idx + total) % total;
            const shift = (100 / total) * current;
            slider.style.transform = `translateX(-${shift}%)`;
            dots.forEach((d,i) => d.classList.toggle('active', i === current));
        }

        function nextSlide() {
            goTo(current + 1);
        }

        function startAutoplay() {
            clearInterval(timer);
            timer = setInterval(nextSlide, 5000);
        }

        dots.forEach((dot, idx) => {
            dot.addEventListener('click', () => {
                goTo(idx);
                startAutoplay();
            });
        });

        goTo(0);
        startAutoplay();
    })();

    let photos = [];
    let videos = [];
    let pdfs   = [];

    fetch('get_media.php')
        .then(res => res.json())
        .then(data => {
            photos = data.photos || [];
            videos = data.videos || [];
            pdfs   = data.pdfs   || [];

            pdfs.forEach(pdf => {
                const selector = `.sablona[data-topic="${pdf.title}"]`;
                const article  = document.querySelector(selector);
                if (article) {
                    const linkElem = article.querySelector('.sablona-link');
                    if (linkElem) linkElem.href = pdf.filepath;
                }
            });

            const photoGrid = document.getElementById('gallery-photo-grid');
            if (photoGrid) {
                photos.forEach(photo => {
                    const title    = photo.title;
                    const filepath = photo.filepath;
                    const keywords = photo.keywords || '';

                    const thumb = document.createElement('div');
                    thumb.className = 'gallery-thumb photo-thumb';
                    thumb.dataset.full     = filepath;
                    thumb.dataset.keywords = keywords;

                    const img = document.createElement('img');
                    img.src = filepath;
                    img.alt = title || '';
                    thumb.appendChild(img);
                    photoGrid.appendChild(thumb);

                    thumb.addEventListener('click', () => {
                        const modal = document.createElement('div');
                        modal.className = 'gallery-image-modal';
                        modal.innerHTML = `
              <div class="gallery-image-overlay"></div>
              <div class="gallery-image-content">
                <button class="gallery-image-close">✕</button>
                <img src="${filepath}" alt="" style="width:100%;height:auto;border-radius:4px;">
              </div>
            `;
                        document.body.appendChild(modal);
                        disablePageScroll();

                        const removeModal = () => {
                            modal.remove();
                            enablePageScroll();
                            window.removeEventListener('keydown', escHandler);
                        };
                        modal.querySelector('.gallery-image-close').onclick   = removeModal;
                        modal.querySelector('.gallery-image-overlay').onclick = removeModal;
                        function escHandler(evt) {
                            if (evt.key === 'Escape') removeModal();
                        }
                        window.addEventListener('keydown', escHandler, { once: true });
                    });
                });
            }

            const videoGrid = document.getElementById('gallery-video-grid');
            if (videoGrid) {
                videos.forEach(vid => {
                    const title    = vid.title;
                    const filepath = vid.filepath;
                    const keywords = vid.keywords || '';

                    const thumb = document.createElement('div');
                    thumb.className = 'gallery-thumb video-thumb';
                    thumb.dataset.video    = filepath;
                    thumb.dataset.keywords = keywords;

                    const vidElem = document.createElement('video');
                    vidElem.muted   = true;
                    vidElem.loop    = true;
                    vidElem.preload = 'metadata';
                    vidElem.style.width     = '100%';
                    vidElem.style.height    = '100%';
                    vidElem.style.objectFit = 'cover';
                    vidElem.src = filepath;
                    thumb.appendChild(vidElem);

                    const overlay = document.createElement('div');
                    overlay.className = 'video-overlay';
                    overlay.innerHTML = `<h3>${title || ''}</h3>`;
                    thumb.appendChild(overlay);

                    videoGrid.appendChild(thumb);

                    thumb.addEventListener('click', () => {
                        const modal = document.createElement('div');
                        modal.className = 'video-modal';
                        modal.innerHTML = `
              <div class="video-modal-content">
                <button class="video-modal-close">✕</button>
                <video src="${filepath}" controls autoplay style="width:100%;"></video>
              </div>
            `;
                        document.body.appendChild(modal);
                        disablePageScroll();

                        const removeModal = () => {
                            modal.remove();
                            enablePageScroll();
                        };
                        modal.querySelector('.video-modal-close').onclick = removeModal;
                        modal.addEventListener('click', evt => {
                            if (evt.target === modal) removeModal();
                        });
                    });
                });
            }

            if (searchInput2) filterGallery(searchInput2.value);
        })
        .catch(err => {
            console.error('Error fetching media:', err);
        });

    document.querySelectorAll('#navody .video-thumb').forEach(thumb => {
        thumb.addEventListener('click', () => {
            const src = thumb.dataset.video;
            if (!src) return;
            const modal = document.createElement('div');
            modal.className = 'video-modal';
            modal.innerHTML = `
        <div class="video-modal-content">
          <button class="video-modal-close">✕</button>
          <video src="${src}" controls autoplay style="width:100%;"></video>
        </div>
      `;
            document.body.appendChild(modal);
            disablePageScroll();

            const removeModal = () => {
                modal.remove();
                enablePageScroll();
            };
            modal.querySelector('.video-modal-close').onclick = removeModal;
            modal.addEventListener('click', evt => {
                if (evt.target === modal) removeModal();
            });
        });
    });

        const sections = [
        document.getElementById('hero'),
        document.getElementById('navody'),
        document.getElementById('sablony'),
        document.getElementById('info'),
    ].filter(el => el !== null);

    const navLinks = Array.from(document.querySelectorAll('.nav__links a[href^="#"]'));

    function setActiveNavLink(activeId) {
        navLinks.forEach((link) => {
            const targetId = link.getAttribute('href').slice(1);
            link.classList.toggle('is-active', targetId === activeId);
        });
    }

    function highlightSection() {
        const viewportMid = window.innerHeight / 2;
        let activeSection = null;

        sections.forEach((sec) => {
            const rect = sec.getBoundingClientRect();
            const isActive = !activeSection && rect.top <= viewportMid && rect.bottom >= viewportMid;

            sec.classList.toggle('active', isActive);
            sec.classList.toggle('inactive', !isActive);

            if (isActive) {
                activeSection = sec;
            }
        });

        if (activeSection) {
            setActiveNavLink(activeSection.id);
        }
    }

    if (sections.length > 0) {
        highlightSection();
    }

    window.addEventListener('scroll', highlightSection);
    window.addEventListener('resize', highlightSection);
    const infoItems = Array.from(document.querySelectorAll('#info .info-item'));
    const infoModal = document.getElementById('info-modal');

    if (infoModal) {
        infoModal.classList.add('hidden');
    }

    function getInfoFileName(index) {
        const baseName = `section${index + 1}`;

        return currentLang === 'sk'
            ? `./info_files/${baseName}.txt`
            : `./info_files/${baseName}_en.txt`;
    }

    function closeInfoCard(item) {
        item.classList.remove('is-flipped');
        item.setAttribute('aria-expanded', 'false');
    }

    function closeOtherInfoCards(activeItem) {
        infoItems.forEach((item) => {
            if (item !== activeItem) {
                closeInfoCard(item);
            }
        });
    }

    function loadInfoBack(item, index) {
        const content = item.querySelector('.info-back-content');
        if (!content) return;

        const fileName = getInfoFileName(index);

        if (content.dataset.fileName === fileName && content.dataset.loaded === 'true') {
            return;
        }

        content.dataset.fileName = fileName;
        content.dataset.loaded = 'false';
        content.textContent = currentLang === 'sk' ? 'Načítavam...' : 'Loading...';

        fetch(fileName)
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Error loading ${fileName}: ${response.status}`);
                }

                return response.text();
            })
            .then((text) => {
                content.textContent = text.trim();
                content.dataset.loaded = 'true';
            })
            .catch((err) => {
                console.error(err);
                content.textContent = currentLang === 'sk'
                    ? 'Text sa nepodarilo načítať.'
                    : 'Text could not be loaded.';
            });
    }

    function flipInfoCard(item, index) {
        const shouldOpen = !item.classList.contains('is-flipped');

        if (shouldOpen) {
            closeOtherInfoCards(item);
            item.classList.add('is-flipped');
            item.setAttribute('aria-expanded', 'true');
            loadInfoBack(item, index);
        } else {
            closeInfoCard(item);
        }
    }

    infoItems.forEach((item, index) => {
        item.classList.add('info-flip-card');
        item.dataset.infoIndex = String(index);
        item.setAttribute('role', 'button');
        item.setAttribute('tabindex', '0');
        item.setAttribute('aria-expanded', 'false');

        if (!item.querySelector('.info-card-inner')) {
            const inner = document.createElement('div');
            inner.className = 'info-card-inner';

            const front = document.createElement('div');
            front.className = 'info-card-face info-card-front';

            Array.from(item.childNodes).forEach((node) => {
                front.appendChild(node);
            });

            const back = document.createElement('div');
            back.className = 'info-card-face info-card-back';
            back.innerHTML = `
                <button type="button" class="info-flip-close" aria-label="Späť">×</button>
                <div class="info-back-content"></div>
            `;

            inner.appendChild(front);
            inner.appendChild(back);
            item.appendChild(inner);
        }

        const hint = item.querySelector('.info-hint');
        if (hint) {
            hint.removeAttribute('href');
            hint.setAttribute('role', 'button');
        }

        item.addEventListener('click', (e) => {
            const target = e.target.closest ? e.target : e.target.parentElement;

            if (target.closest('.info-flip-close')) {
                e.preventDefault();
                e.stopPropagation();
                closeInfoCard(item);
                return;
            }

            if (target.closest('a')) {
                e.preventDefault();
            }

            flipInfoCard(item, index);
        });

        item.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeInfoCard(item);
                return;
            }

            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                flipInfoCard(item, index);
            }
        });
    });

    const translateBtn = document.getElementById('translate-btn');
    if (translateBtn) {
        translateBtn.addEventListener('click', () => {
            toggleTranslation();
        });
    }
});

let pull_id;
let user_id;
let total_restaurant = 0;
let current_index = 0;
let choose_result = { love: [], nope: [] };
let restaurants = [];
let firstLoad = true

$(document).ready(function () {
    parseParam();
})

function rightSlideIn() {
    document.getElementById("left_content").setAttribute("style", "display: block !important;");
    setTimeout(leftSlideIn, 1000);
}

function leftSlideIn() {
    document.getElementById("right_content").setAttribute("style", "display: block !important;");
    setTimeout(btnEaseIn, 1000)
}

function btnEaseIn() {
    $("#button_hint").fadeIn();
}

function hideHint() {
    Swal.fire({
        icon: "question",
        title: "是否要永久關閉提示？",
        confirmButtonText: "確認",
        showCancelButton: true,
        cancelButtonText: "取消",
    }).then((result) => {
        if (result.isConfirmed) {
            localStorage["dont_hint"] = true
        }
    })
    document.getElementById("hint_box").setAttribute("style", "display: none;");
}

function initializeLiff(myLiffId) {
    liff
        .init({
            liffId: myLiffId,
        })
        .then(() => {
            initializeApp();
        })
        .catch((err) => {
            console.log(err);
        });
}

function initializeApp() {
    let currentTime = new Date()

    if (!liff.isLoggedIn()) {
        if (localStorage["lastLogin"] && Math.ceil(new Date(localStorage["lastLogin"]).getTime() - currentTime.getTime() / (1000 * 3600 * 24)) > 1) {
            loadPage();
        } else {
            liff.login();
        }
    } else {
        liff
            .getProfile()
            .then((profile) => {
                user_id = profile.userId;
                localStorage["user_id"] = user_id

                loadPage();
            })
            .catch((err) => {
                console.log(err);
            });
    }
}

function loadPage() {
    current_index = 0;
    choose_result = { love: [], nope: [] };
    $(".loading_page").fadeOut();
    $(".tinder").fadeIn();
    if (!localStorage["dont_hint"] || localStorage["dont_hint"] == "false") {
        document.getElementById("hint_box").setAttribute("style", "display: block;");
        rightSlideIn();
    }
    var tinderContainer = document.querySelector(".tinder");
    var allCards = document.querySelectorAll(".tinder--card");

    function initCards(card, index) {
        var newCards = document.querySelectorAll(".tinder--card:not(.removed)")

        newCards.forEach(function (card, index) {
            card.style.zIndex = allCards.length - index
            card.style.transform = "scale(" + (20 - index) / 20 + ") translateY(-" + 30 * index + "px)"
            card.style.opacity = (10 - index) / 10
        })

        tinderContainer.classList.add("loaded")
    }

    initCards();
    fetch_restaurant();
}

function parseParam() {
    const query_url = new URL(window.location.href)
    const query_params = new URLSearchParams(query_url.searchParams.get("liff.state"))

    if (query_params.get("pull_id") != null) {
        pull_id = query_params.get("pull_id")
        localStorage["pull_id"] = pull_id
    } else {
        if (query_url.searchParams.get("pull_id") != null) {
            pull_id = query_url.searchParams.get("pull_id")
            localStorage["pull_id"] = pull_id
        } else {
            pull_id = localStorage["pull_id"]
        }
    }
    initializeLiff("1655422218-8n1PlOw1");
}

function fetch_restaurant() {
    if (firstLoad) {
        const requestOptions = {
            method: 'GET',
            header: { 'Content-Type': 'application/json' },
            mode: 'same-origin'
        };
        const requestURL = `/api/vote/get/restaurant?pull_id=${pull_id}`

        fetch(requestURL, requestOptions)
            .then(response => response.json())
            .then((data) => {
                if (data.status == "success") {
                    $("#cardWrapper").empty()
                    restaurants = data.restaurants
                    total_restaurant = restaurants.length
                    restaurants.forEach(i => renderCard(i))
                    main()
                } else {
                    Swal.fire({
                        icon: "error",
                        title: "很抱歉！",
                        text: data.error_message,
                        confirmButtonText: "確認",
                    })
                }
            })
            .catch((error) => {
                Swal.fire({
                    icon: "error",
                    title: "很抱歉！",
                    text: "無法連接伺服器，請稍後再試！",
                    confirmButtonText: "確認",
                })
                console.log(error)
            });
    } else {
        $("#cardWrapper").empty()
        restaurants.forEach(i => renderCard(i))
        main()
    }
}

function renderCard(restaurantInfo) {
    let price = "";
    if (restaurantInfo.price > 0) {
        price = "$" + restaurantInfo.price
    } else {
        price = "未知"
    }
    const data = `
    <div class='tinder--card'>
        <div class='main-window' id='main-window'>
            <div class='restaurant-image' style="background-image: url('${restaurantInfo.photo_url}');">
                <div class='restaurant-name'>${restaurantInfo.name}</div>
            </div>
            <div class='restaurant-info'>
                <div class='address'>地點：${restaurantInfo.address}</div>
            </div>
  
            <div class='detail-info'>
                <div class='detail-info-elm'>評價<br><span class='lg'>${restaurantInfo.rating}</span></div>
                <div class='detail-info-elm'>價位<br><span class='lg'>${price}</span></div>
                <div class='detail-info-elm'>關鍵字<br><span class='sm'>${restaurantInfo.keywords.join(", ")}</span></div>
            </div>
        </div>
    </div>`
    $("#cardWrapper").append(data)
}

function main() {
    var tinderContainer = document.querySelector(".tinder")
    var allCards = document.querySelectorAll(".tinder--card")
    var nope = document.getElementById("nope")
    var love = document.getElementById("love")

    function initCards(card, index) {
        var newCards = document.querySelectorAll(".tinder--card:not(.removed)")

        newCards.forEach(function (card, index) {
            card.style.zIndex = allCards.length - index
            card.style.transform = "scale(" + (20 - index) / 20 + ") translateY(-" + 30 * index + "px)"
            card.style.opacity = (10 - index) / 10
        })

        tinderContainer.classList.add("loaded")
    }

    initCards()

    allCards.forEach(function (el) {
        var hammertime = new Hammer(el)

        hammertime.on("pan", function (event) {
            el.classList.add("moving")
        })

        hammertime.on("pan", function (event) {
            if (event.deltaX === 0) return
            if (event.center.x === 0 && event.center.y === 0) return

            tinderContainer.classList.toggle("tinder_love", event.deltaX > 0)
            tinderContainer.classList.toggle("tinder_nope", event.deltaX < 0)
            var xMulti = event.deltaX * 0.03
            var yMulti = event.deltaY / 80
            var rotate = xMulti * yMulti
            var cards = document.querySelectorAll(".tinder--card:not(.removed)")
            var card = cards[0]

            card.style.transform = "translate(" + event.deltaX + "px, " + event.deltaY + "px) rotate(" + rotate + "deg)"
        })

        hammertime.on("panend", function (event) {
            el.classList.remove("moving")
            tinderContainer.classList.remove("tinder_love")
            tinderContainer.classList.remove("tinder_nope")

            var moveOutWidth = document.body.clientWidth
            var keep = Math.abs(event.deltaX) < 80 || Math.abs(event.velocityX) < 0.5
            var cards = document.querySelectorAll(".tinder--card:not(.removed)")
            var card = cards[0]

            card.classList.toggle("removed", !keep)

            if (keep) {
                card.style.transform = ""
            } else {
                if (event.deltaX > 0) {
                    love_restaurant()
                } else {
                    not_love_restaurant()
                }
                var endX = Math.max(Math.abs(event.velocityX) * moveOutWidth, moveOutWidth)
                var toX = event.deltaX > 0 ? endX : -endX
                var endY = Math.abs(event.velocityY) * moveOutWidth
                var toY = event.deltaY > 0 ? endY : -endY
                var xMulti = event.deltaX * 0.03
                var yMulti = event.deltaY / 80
                var rotate = xMulti * yMulti

                card.style.transform =
                    "translate(" + toX + "px, " + (toY + event.deltaY) + "px) rotate(" + rotate + "deg)"
                initCards()
            }
        })
    })

    function createButtonListener(love) {
        return function (event) {
            var cards = document.querySelectorAll(".tinder--card:not(.removed)")
            var moveOutWidth = document.body.clientWidth * 1.5

            if (!cards.length) return false

            var card = cards[0]
            card.classList.add("removed")

            if (love) {
                love_restaurant()
                card.style.transform = "translate(" + moveOutWidth + "px, -100px) rotate(-30deg)"
            } else {
                not_love_restaurant()
                card.style.transform = "translate(-" + moveOutWidth + "px, -100px) rotate(30deg)"
            }

            initCards()

            event.preventDefault()
        }
    }
    if (firstLoad) {
        var nopeListener = createButtonListener(false)
        var loveListener = createButtonListener(true)

        nope.addEventListener("click", nopeListener)
        love.addEventListener("click", loveListener)
    }
}

function love_restaurant() {
    const restaurantID = restaurants[current_index]["place_id"]
    localStorage[restaurantID] = restaurants[current_index]["name"]
    choose_result["love"].push(restaurantID)
    current_index += 1
    if (current_index == total_restaurant) {
        save_results()
    }
}

function not_love_restaurant() {
    const restaurantID = restaurants[current_index]["place_id"]
    localStorage[restaurantID] = restaurants[current_index]["name"]
    choose_result["nope"].push(restaurantID)
    current_index += 1
    if (current_index == total_restaurant) {
        save_results()
    }
}

function save_results() {
    firstLoad = false;
    let loveRestaurants = [];
    let nopeRestaurants = [];
    for (i in choose_result["love"]) {
        restaurantName = localStorage[choose_result["love"][i]]
        loveRestaurants.push(restaurantName)
    }
    for (i in choose_result["nope"]) {
        restaurantName = localStorage[choose_result["nope"][i]]
        nopeRestaurants.push(restaurantName)
    }
    let LoveText = ""
    let NopeText = ""
    for (i in loveRestaurants) {
        temp = `<li class="checkLoveText">${loveRestaurants[i]}</li>`
        LoveText += temp
    }
    for (i in nopeRestaurants) {
        temp = `<li class="checkNopeText">${nopeRestaurants[i]}</li>`
        NopeText += temp
    }
    let checkText = `
    <p style="color:green; text-align: left;">喜歡：${LoveText}</p>
    <p style="color:red; text-align: left;">不喜歡：${NopeText}</p>
    `

    Swal.fire({
        icon: "question",
        title: "請確認投票選擇",
        html: checkText,
        confirmButtonText: "確認送出",
        showCancelButton: true,
        cancelButtonText: "重新選擇",
        showLoaderOnConfirm: true,
        preConfirm: (login) => {
            const sendData = {
                pull_id,
                user_id,
                choose_result,
            };
            const requestOptions = {
                method: 'POST',
                header: { 'Content-Type': 'application/json' },
                body: JSON.stringify(sendData),
                mode: 'same-origin'
            };
            const requestURL = "/api/vote/save/restaurant";
            return fetch(requestURL, requestOptions)
                .then(response => {
                    return response.json()
                })
                .catch(error => {
                    console.log(error)
                    Swal.showValidationMessage(
                        "無法連接伺服器，請稍後再試！"
                    )
                })
        },
        allowOutsideClick: () => !Swal.isLoading()
    }).then((result) => {
        if (result.isConfirmed) {
            if (result.value.status == "success") {
                fetchVoteDate();
            } else {
                Swal.fire({
                    icon: "error",
                    title: "很抱歉！",
                    text: data.result,
                    confirmButtonText: "確認",
                })
            }
        } else {
            loadPage();
        }
    })
}

function fetchVoteDate() {
    const requestOptions = {
        method: 'GET',
        header: { 'Content-Type': 'application/json' },
        mode: 'same-origin'
    };
    const requestURL = `/api/vote/get/date?pull_id=${pull_id}`

    fetch(requestURL, requestOptions)
        .then(response => response.json())
        .then((data) => {
            if (data.status == "success") {
                Swal.fire({
                    icon: "success",
                    title: "儲存成功！",
                    text: "將在1秒後轉往日期投票...",
                    timer: 1000,
                });
                document.getElementById("voteTitle").innerHTML = data.data.vote_name;
                $("#dateTable").empty()
                const voteTitle = `<h3>選擇時間</h3>`
                $("#dateTable").append(data)
                let totalDates = []
                Object.keys(data.data.dates).forEach((key) => {
                    totalDates.push(key)
                    let ok, unsure, cancel = 0;
                    Object.keys(data.data.dates[key]).forEach((each_key) => {
                        localStorage[`${key}_${each_key}`] = data.data.dates[key][each_key]
                        if (each_key == "ok") {
                            ok = data.data.dates[key][each_key]
                        } else if (each_key == "unsure") {
                            unsure = data.data.dates[key][each_key]
                        } else {
                            cancel = data.data.dates[key][each_key]
                        }
                    })
                    renderDates(key, ok, unsure, cancel)
                });
                localStorage["totalDates"] = totalDates
                setTimeout(() => {
                    document.getElementsByTagName('body')[0].style = 'overflow: visible;';
                    $(".tinder").fadeOut();
                    $("#schedular").fadeIn();
                }, 1700)
            } else {
                Swal.fire({
                    icon: "error",
                    title: "很抱歉！",
                    text: data.error_message,
                    confirmButtonText: "確認",
                })
            }
        })
        .catch((error) => {
            Swal.fire({
                icon: "error",
                title: "很抱歉！",
                text: "無法連接伺服器，請稍後再試！",
                confirmButtonText: "確認",
            })
            console.log(error)
        });
}

function renderDates(dateTitle, okCount, unsureCount, cancelCount) {
    const data = `
    <div class="date-info">
        <div class="date-title">
            <span>${dateTitle}</span>
        </div>
        <div class="row date-choose">
            <div class="col">
                <button class="btn ok-icon" onclick="okButton($(this))" id="ok_${dateTitle}">
                    <p class="icon-text">
                        <i class="fas fa-check-circle"></i>
                        <span id="ok_users_count_${dateTitle}">${okCount}</span>
                    </p>
                </button>
            </div>
            <div class="col">
                <button class="btn unsure-icon" onclick="unsureButton($(this))" id="unsure_${dateTitle}">
                    <p class="icon-text" id="unsure_users_count">
                        <i class="fas fa-question-circle"></i>
                        <span id="unsure_users_count_${dateTitle}">${unsureCount}</span>
                    </p>
                </button>
            </div>
            
            <div class="col">
                <button class="btn cancel-icon" onclick="cancelButton($(this))" id="cancel_${dateTitle}">
                    <p class="icon-text" id="cancel_users_count">
                        <i class="fas fa-ban"></i>
                        <span id="cancel_users_count_${dateTitle}">${cancelCount}</span>
                    </p>
                </button>
            </div>
            
        </div>
    </div>`
    $("#dateTable").append(data)
}
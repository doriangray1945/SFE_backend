from django.shortcuts import render

cities = [
    {
        "id": 1,
        "name": "Элиста",
        "population": "107 тыс.",
        "salary": "35",
        "unemployment_rate": "6.1",
        "description": "Элиста – столица Калмыкии, город, сочетающий в себе традиции кочевого народа и современный образ жизни.  Развитая инфраструктура и уникальный колорит Элисты привлекают как туристов, так и специалистов, готовых к развитию региона.",
        "image": "http://localhost:9000/images/1.png"
    },
    {
        "id": 2,
        "name": "Москва",
        "population": "13.1 млн.",
        "salary": "150",
        "unemployment_rate": "3.4",
        "description": "Москва — это крупнейший экономический центр России, где сосредоточено множество высококвалифицированных специалистов и ведущих компаний. Размещение вакансии в этом городе открывает доступ к широкому рынку труда и перспективным кандидатам.",
        "image": "http://localhost:9000/images/2.png"
    },
    {
        "id": 3,
        "name": "Калининград",
        "population": "498 тыс.",
        "salary": "64",
        "unemployment_rate": "0.4",
        "description": "Калининград - это динамичный город с богатой историей и развитой инфраструктурой. Он  расположен в стратегическом  месте,  на  берегу  Балтийского  моря.  Размещение  вакансии  в  Калининграде  открывает  доступ  к  квалифицированным  кадрам  и  возможностям  для  развития  бизнеса.",
        "image": "http://localhost:9000/images/3.png"
    },
    {
        "id": 4,
        "name": "Великий Новгород",
        "population": "223 тыс.",
        "salary": "65",
        "unemployment_rate": "1.7",
        "description": "Великий Новгород - это исторический город с богатым культурным наследием и развитой инфраструктурой. Он  расположен на берегу  реки  Волхов  и  является  центром  туризма  и  образования.  Размещение  вакансии  в  Новгороде  открывает  доступ  к  квалифицированным  кадрам  и  спокойной  атмосфере  для  работы.",
        "image": "http://localhost:9000/images/4.png"
    },
    {
        "id": 5,
        "name": "Казань",
        "population": "1.2 млн.",
        "salary": "74",
        "unemployment_rate": "0.21",
        "description": "Казань – столица Татарстана,  динамичный город с богатым культурным наследием и развитой инфраструктурой.  Он  является  центром  образования,  туризма  и  бизнеса.  Размещение  вакансии  в  Казани  открывает  доступ  к  квалифицированным  кадрам  и  возможностям  для  развития  карьеры.",
        "image": "http://localhost:9000/images/5.png"
    }
]

draft_application = {
    "id": 1,
    "date_created": "21 сентября 2024г",
    "vacancy": {
        "name": "Врач-невролог",
        "responsibilities": "оказание квалифицированной лечебно-профилактической помощи детям, ведение амбулаторного приема",
        "requirements": "высшее медицинское образование, опыт работы не менее 3-х лет по специальности, клиентоориентированность"
    },
    "cities": [
        {
            "id": 1,
            "name": "Элиста",
            "image": "http://localhost:9000/images/1.png",
            "count": 2
        },
        {
            "id": 4,
            "name": "Новгород",
            "image": "http://localhost:9000/images/2.png",
            "count": 3
        },
        {
            "id": 5,
            "name": "Казань",
            "image": "http://localhost:9000/images/3.png",
            "count": 4
        }
    ]
}


def getCityById(city_id):
    for city in cities:
        if city["id"] == city_id:
            return city


def searchCities(city_name):
    res = []

    for city in cities:
        if city_name.lower() in city["name"].lower():
            res.append(city)

    return res


def getDraftApplication():
    return draft_application


def getApplicationById(application_id):
    return draft_application


def open(request):
    city_name = request.GET.get("city_name", "")
    cities = searchCities(city_name)

    context = {
        "cities": cities,
        "city_name": city_name,
        "cities_count": len(draft_application["cities"]),
        "draft_application": draft_application
    }

    return render(request, "home_page.html", context)


def city(request, city_id):
    context = {
        "id": city_id,
        "city": getCityById(city_id),
    }

    return render(request, "city_page.html", context)


def application(request, application_id):
    context = {
        "application": getApplicationById(application_id),
    }

    return render(request, "application_page.html", context)


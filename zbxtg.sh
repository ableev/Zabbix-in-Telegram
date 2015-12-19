#!/bin/bash

. $(dirname "$0")/tg_vars.cfg

CURL_TG="${CURL} https://api.telegram.org/bot${TG_KEY}"

TMP_DIR="/tmp/${ZBX_TG_PREFIX}"
[ ! -d "${TMP_DIR}" ] && (mkdir -p ${TMP_DIR} || TMP_DIR="/tmp")
TMP_COOKIE="${TMP_DIR}/cookie.txt"
TMP_UIDS="${TMP_DIR}/uids.txt"

login() {
    # grab cookie for downloading image
    ${CURL} --cookie-jar ${TMP_COOKIE} --request POST --data "name=${ZBX_API_USER}&password=${ZBX_API_PASS}&enter=Sign%20in" ${ZBX_SERVER}/
}

get_image() {
    URL=$1
    IMG_NAME=$2
    # downloads png graph and saves it to temporary path
    ${CURL} -s --cookie ${TMP_COOKIE} --globoff "${URL}" -o ${IMG_NAME}
}

TO=$1
SUBJECT=$2
BODY=$3

TG_CHAT=0 # send message to chat or to private chat to user
METHOD="txt" # sendMessage (simple text) or sendPhoto (attached image)

echo "${BODY}" | grep -q "${ZBX_TG_PREFIX};graphs" && METHOD="image"
echo "${BODY}" | grep -q "${ZBX_TG_PREFIX};chat" && TG_CHAT=1

TG_CHAT_ID=$(cat ${TMP_UIDS} | awk -F ';' END'{ print $NF}')

if [ -z "${TG_CHAT_ID}" ]
then
    TG_UPDATES=$(${CURL_TG}/getUpdates)
    TG_CHAT_ID=$(echo "${TG_UPDATES}" | awk -F ',' END'{print $6}' | sed 's/"chat":{"id"://g;/^$/d'
    
    echo "${TO};${TG_CHAT_ID}" >> ${TMP_UIDS}
fi

TG_TEXT=$(echo "${BODY}" | grep -vE "^${ZBX_TG_PREFIX};"; echo "--")

case "${METHOD}" in

    "txt")
        ${CURL_TG}/sendMessage -F "chat_id=${TG_CHAT_ID}" -F "text=${SUBJECT}
${TG_TEXT}" 2>/dev/null
    ;;

    "image")
        PERIOD=3600 # default period
        echo "${BODY}" | grep -q "^${ZBX_TG_PREFIX};graphs_period" && PERIOD=$(echo "${BODY}" | awk -F '=' /graphs_period/'{print $NF}')  || PERIOD=3600
        ZBX_ITEMID=$(echo "${BODY}" | awk -F ':' /itemid/'{print $NF}')
        ZBX_TITLE=$(echo "${BODY}" | awk -F ':' /title/'{print $NF}')
        URL="${ZBX_SERVER}/chart3.php?period=${PERIOD}&name=${ZBX_TITLE}&width=900&height=200&graphtype=0&legend=1&items[0][itemid]=${ZBX_ITEMID}&items[0][sortorder]=0&items[0][drawtype]=5&items[0][color]=00CC00"
        login
        CACHE_IMAGE="${TMP_DIR}/graph.${ZBX_ITEMID}.png"
        get_image "${URL}" ${CACHE_IMAGE}
        ${CURL_TG}/sendPhoto -F "chat_id=${TG_CHAT_ID}" -F "caption=${SUBJECT}
${TG_TEXT}" -F "photo=@${CACHE_IMAGE}" 2>/dev/null
        rm ${CACHE_IMAGE}
    ;;

esac

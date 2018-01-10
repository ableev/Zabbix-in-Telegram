#!/bin/bash

. $(dirname "$0")/tg_vars.cfg

CURL_TG="${CURL} https://api.telegram.org/bot${TG_KEY}"

TMP_DIR="/tmp/${ZBX_TG_PREFIX}"
[ ! -d "${TMP_DIR}" ] && (mkdir -p ${TMP_DIR} || TMP_DIR="/tmp")
TMP_COOKIE="${TMP_DIR}/cookie.txt"
TMP_UIDS="${TMP_DIR}/uids.txt"

TS="`date +%s_%N`_$RANDOM"
LOG="/dev/null"

IS_DEBUG () {
    if [ "${ISDEBUG}" == "TRUE" ]
    then
        return 0
    else
        return 1
    fi
}


login() {
    # grab cookie for downloading image
    IS_DEBUG && echo "${CURL} --cookie-jar ${TMP_COOKIE} --request POST --data \"name=${ZBX_API_USER}&password=${ZBX_API_PASS}&enter=Sign%20in\" ${ZBX_SERVER}/" >>${LOG}
    ${CURL} --cookie-jar ${TMP_COOKIE} --request POST --data "name=${ZBX_API_USER}&password=${ZBX_API_PASS}&enter=Sign%20in" ${ZBX_SERVER}/
}

get_image() {
    URL=$1
    URL=$(echo "${URL}" | sed -e 's/\ /%20/g')
    IMG_NAME=$2
    # downloads png graph and saves it to temporary path
    IS_DEBUG && echo "${CURL} --cookie ${TMP_COOKIE} --globoff \"${URL}\" -o ${IMG_NAME}" >>${LOG}
    ${CURL} --cookie ${TMP_COOKIE} --globoff "${URL}" -o ${IMG_NAME}
}

TO=$1
SUBJECT=$2
BODY=$3

TG_GROUP=0 # send message to chat or to private chat to user
TG_CHANNEL=0 # send message to channel
METHOD="txt" # sendMessage (simple text) or sendPhoto (attached image)

echo "${BODY}" | grep -q "${ZBX_TG_PREFIX};graphs" && METHOD="image"
echo "${BODY}" | grep -q "${ZBX_TG_PREFIX};chat" && TG_GROUP=1
echo "${BODY}" | grep -q "${ZBX_TG_PREFIX};group" && TG_GROUP=1
echo "${BODY}" | grep -q "${ZBX_TG_PREFIX};debug" && ISDEBUG="TRUE"
echo "${BODY}" | grep -q "${ZBX_TG_PREFIX};channel" && TG_CHANNEL=1

IS_DEBUG && LOG="${TMP_DIR}/debug.${TS}.log"
IS_DEBUG && echo -e "TMP_DIR=${TMP_DIR}\nTMP_COOKIE=${TMP_COOKIE}\nTMP_UIDS=${TMP_UIDS}" >>${LOG}

if [ "${TG_GROUP}" -eq 1 ]
then
    TG_CONTACT_TYPE="group"
else
    TG_CONTACT_TYPE="private"
fi

TG_CHAT_ID=$(cat ${TMP_UIDS} | awk -F ';' '{if ($1 == "'${TO}'" && $2 == "'${TG_CONTACT_TYPE}'") print $3}' | tail -1)

if [ "${TG_CHANNEL}" -eq 1 ]
then
    TG_CHAT_ID="${TO}"
fi

if [ -z "${TG_CHAT_ID}" ]
then
    TG_UPDATES=$(${CURL_TG}/getUpdates | sed -e 's/},{/\n/')
    for (( idx=${#TG_UPDATES[@]}-1 ; idx>=0 ; idx-- ))
    do
        UPDATE="${TG_UPDATES[idx]}"
        echo "${UPDATE}"
        if [ "${TG_GROUP}" -eq 1 ]
        then
            TG_CHAT_ID=$(echo "${UPDATE}" | sed -e 's/["}{]//g' | awk -F ',' '{if ($8 == "type:group" && $7 == "title:'${TO}'") {gsub("chat:id:", "", $6); print $6}}' | tail -1)
            if [ "$(echo ${TG_CHAT_ID} | grep -Eq '\-[0-9]+' && echo 1 || echo 0)" -eq 1 ]
            then
                break
            fi
        else
            TG_CHAT_ID=$(echo "${UPDATE}" | sed -e 's/["}{]//g' | awk -F ',' '{if ($10 == "type:private" && $5 == "username:'${TO}'") {gsub("chat:id:", "", $6); print $6}}' | tail -1)
            if [ "$(echo ${TG_CHAT_ID} | grep -Eq '[0-9]+' && echo 1 || echo 0)" -eq 1 ]
            then
                break
            fi
        fi
    done
    echo "${TO};${TG_CONTACT_TYPE};${TG_CHAT_ID}" >>${TMP_UIDS}
fi

IS_DEBUG && echo "TG_CHAT_ID: ${TG_CHAT_ID}" >>${LOG}

TG_TEXT=$(echo "${BODY}" | grep -vE "^${ZBX_TG_PREFIX};")
if [ "${ZBX_TG_SIGN}" != "FALSE" ]
then
    TG_TEXT=$(echo ${TG_TEXT}; echo "--"; echo "${ZBX_SERVER}")
fi

case "${METHOD}" in

    "txt")
        TG_MESSAGE=$(echo -e "${SUBJECT}\n${TG_TEXT}")
        IS_DEBUG && echo "${CURL_TG}/sendMessage -F \"chat_id=${TG_CHAT_ID}\" -F \"text=${TG_MESSAGE}\"" >>${LOG}
        ANSWER=$(${CURL_TG}/sendMessage?chat_id=${TG_CHAT_ID} --form "text=${TG_MESSAGE}" 2>&1)
        if [ "$(echo "${ANSWER}" | grep -Ec 'migrated.*supergroup')" -eq 1 ]
        then
            migrate_to_chat_id=$(echo "${ANSWER}" | sed -e 's/["}{]//g' | grep -Eo '\-[0-9]+$')
            echo "${TO};${TG_CONTACT_TYPE};${migrate_to_chat_id}" >>${TMP_UIDS}
            ANSWER=$(${CURL_TG}/sendMessage?chat_id=${migrate_to_chat_id} --form "text=${TG_MESSAGE}" 2>&1)
        fi
    ;;

    "image")
        PERIOD=3600 # default period
        echo "${BODY}" | grep -q "^${ZBX_TG_PREFIX};graphs_period" && PERIOD=$(echo "${BODY}" | awk -F "${ZBX_TG_PREFIX};graphs_period=" '{if ($2 != "") print $2}' | tail -1 | grep -Eo '[0-9]+' || echo 3600)
        ZBX_ITEMID=$(echo "${BODY}" | awk -F "${ZBX_TG_PREFIX};itemid:" '{if ($2 != "") print $2}' | tail -1 | grep -Eo '[0-9]+')
        ZBX_TITLE=$(echo "${BODY}" | awk -F "${ZBX_TG_PREFIX};title:" '{if ($2 != "") print $2}' | tail -1)
        URL="${ZBX_SERVER}/chart3.php?period=${PERIOD}&name=${ZBX_TITLE}&width=900&height=200&graphtype=0&legend=1&items[0][itemid]=${ZBX_ITEMID}&items[0][sortorder]=0&items[0][drawtype]=5&items[0][color]=00CC00"
        IS_DEBUG && echo "Zabbix graph URL: ${URL}" >> ${LOG}
        login
        CACHE_IMAGE="${TMP_DIR}/graph.${ZBX_ITEMID}.png"
        IS_DEBUG && echo "Image cached to ${CACHE_IMAGE} and wasn't deleted" >> ${LOG}
        get_image "${URL}" ${CACHE_IMAGE}
        TG_CAPTION_ORIG=$(echo -e "${SUBJECT}\n${TG_TEXT}")
        TG_CAPTION=$(echo -e $(echo "${TG_CAPTION_ORIG}" | sed ':a;N;$!ba;s/\n/\\n/g' | awk '{print substr( $0, 0, 200 )}'))
        if [ "${TG_CAPTION}" != "${TG_CAPTION_ORIG}" ]
        then
            echo "${ZBX_TG_PREFIX}: probably you will see MEDIA_CAPTION_TOO_LONG error, the message has been cut to 200 symbols, https://github.com/ableev/Zabbix-in-Telegram/issues/9#issuecomment-166895044"
        fi
        IS_DEBUG && echo "${CURL_TG}/sendPhoto?chat_id=${TG_CHAT_ID}\" --form \"caption=${TG_CAPTION}\" -F \"photo=@${CACHE_IMAGE}\"" >>${LOG}
        ANSWER=$(${CURL_TG}/sendPhoto?chat_id=${TG_CHAT_ID} --form "caption=${TG_CAPTION}" -F "photo=@${CACHE_IMAGE}")
        IS_DEBUG || rm ${CACHE_IMAGE}
    ;;

esac

echo >>${LOG}

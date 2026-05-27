-- --------------------------------------------------------
-- 호스트:                          localhost
-- 서버 버전:                        8.0.45 - MySQL Community Server - GPL
-- 서버 OS:                        Win64
-- HeidiSQL 버전:                  12.12.0.7122
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- lol 데이터베이스 구조 내보내기
CREATE DATABASE IF NOT EXISTS `lol` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `lol`;

-- 테이블 lol.lol_game_data 구조 내보내기
CREATE TABLE IF NOT EXISTS `lol_game_data` (
  `game_id` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `game_length` int NOT NULL COMMENT '게임 시간 (초 단위)',
  `version` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '클라이언트 패치 버전',
  `game_date` datetime NOT NULL COMMENT '게임 시작 시각',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT 'DB 적재 시각',
  PRIMARY KEY (`game_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 내보낼 데이터가 선택되어 있지 않습니다.

-- 테이블 lol.lol_game_data_participant 구조 내보내기
CREATE TABLE IF NOT EXISTS `lol_game_data_participant` (
  `game_id` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `participant_id` int NOT NULL COMMENT '1 ~ 10 번 참여자 번호',
  `team_id` int NOT NULL COMMENT '100 또는 200',
  `puuid` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `summoner_name` varchar(250) DEFAULT NULL COMMENT 'Riot ID (Name#Tag)',
  `summoner_tier` varchar(50) DEFAULT NULL,
  `summoner_rank` varchar(50) DEFAULT NULL,
  `position` enum('TOP','JUNGLE','MID','ADC','SUPPORT','UNKNOWN') DEFAULT 'UNKNOWN',
  `champion_id` int NOT NULL,
  `is_won` tinyint(1) DEFAULT '0',
  `kill` int DEFAULT '0',
  `death` int DEFAULT '0',
  `assist` int DEFAULT '0',
  `kda` decimal(20,6) DEFAULT NULL,
  `level` int DEFAULT NULL,
  `total_cs` int DEFAULT '0',
  `total_gold` int DEFAULT '0',
  `total_damage_to_champions` decimal(20,6) DEFAULT '0.000000',
  `total_damage_taken` decimal(20,6) DEFAULT '0.000000',
  `cspm` decimal(20,6) DEFAULT NULL COMMENT '분당 CS',
  `kp` decimal(20,6) DEFAULT NULL COMMENT '킬 관여율 (Kill Participation)',
  `ward_placed` int DEFAULT '0',
  `control_ward_placed` int DEFAULT '0',
  `ward_kill` int DEFAULT '0',
  `tower_kill` int DEFAULT '0',
  `dragon_kill` int DEFAULT '0',
  `baron_kill` int DEFAULT '0',
  `items` json DEFAULT NULL COMMENT '[item0, item1, ... item6]',
  `perks` json DEFAULT NULL COMMENT '룬 스타일 및 핵심 룬 데이터',
  `summoner_spell` json DEFAULT NULL COMMENT '[spell1_id, spell2_id]',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`game_id`,`participant_id`) USING BTREE,
  KEY `puuid` (`puuid`) USING BTREE,
  KEY `position` (`position`) USING BTREE,
  KEY `FK_participant_team` (`game_id`,`team_id`),
  CONSTRAINT `FK_participant_game_data` FOREIGN KEY (`game_id`) REFERENCES `lol_game_data` (`game_id`) ON DELETE CASCADE,
  CONSTRAINT `FK_participant_team` FOREIGN KEY (`game_id`, `team_id`) REFERENCES `lol_game_data_team` (`game_id`, `team_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 내보낼 데이터가 선택되어 있지 않습니다.

-- 테이블 lol.lol_game_data_team 구조 내보내기
CREATE TABLE IF NOT EXISTS `lol_game_data_team` (
  `game_id` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `team_id` int NOT NULL COMMENT '블루팀: 100, 레드팀: 200',
  `is_won` tinyint(1) DEFAULT '0' COMMENT '팀 승리 여부 (1: 승리, 0: 패배)',
  `tower_kill` int DEFAULT '0' COMMENT '팀 총 타워 파괴 수',
  `dragon_kill` int DEFAULT '0' COMMENT '팀 총 드래곤 처치 수',
  `baron_kill` int DEFAULT '0' COMMENT '팀 총 바론 처치 수',
  `total_kill` int DEFAULT '0' COMMENT '팀 총 킬 수 (팀 KP 계산용)',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`game_id`,`team_id`) USING BTREE,
  CONSTRAINT `FK_team_game_data` FOREIGN KEY (`game_id`) REFERENCES `lol_game_data` (`game_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 내보낼 데이터가 선택되어 있지 않습니다.

-- 테이블 lol.lol_game_data_timeline 구조 내보내기
CREATE TABLE IF NOT EXISTS `lol_game_data_timeline` (
  `game_id` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `participant_id` int NOT NULL COMMENT '1 ~ 10 번 참여자 번호',
  `minute` int NOT NULL COMMENT '게임 시간 (분 단위, 0부터 시작)',
  `timestamp_ms` bigint NOT NULL COMMENT '실제 밀리초 단위 타임스탬프',
  `level` int DEFAULT '1' COMMENT '해당 분(Minute)의 레벨',
  `experience` int DEFAULT '0' COMMENT '누적 경험치량',
  `total_gold` int DEFAULT '0' COMMENT '누적 획득 골드',
  `current_gold` int DEFAULT '0' COMMENT '현재 보유 골드',
  `minions_killed` int DEFAULT '0' COMMENT '라인 미니언 처치 수',
  `jungle_minions_killed` int DEFAULT '0' COMMENT '정글 몬스터 처치 수',
  `damage_stats` json DEFAULT NULL COMMENT '챔피언에게 가한 누적 피해량 등 JSON 저장',
  `position_x` int DEFAULT NULL COMMENT '해당 분의 X 좌표',
  `position_y` int DEFAULT NULL COMMENT '해당 분의 Y 좌표',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`game_id`,`participant_id`,`minute`) USING BTREE,
  CONSTRAINT `FK_timeline_participant` FOREIGN KEY (`game_id`, `participant_id`) REFERENCES `lol_game_data_participant` (`game_id`, `participant_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 내보낼 데이터가 선택되어 있지 않습니다.

-- 테이블 lol.lol_match_list 구조 내보내기
CREATE TABLE IF NOT EXISTS `lol_match_list` (
  `match_id` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `puuid` varchar(200) DEFAULT NULL COMMENT '수집 출처 PUUID',
  `status` tinyint(1) DEFAULT '0' COMMENT '0: 대기, 1: 처리완료, 2: 에러',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`match_id`) USING BTREE,
  KEY `status_idx` (`status`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 내보낼 데이터가 선택되어 있지 않습니다.

-- 테이블 lol.lol_player 구조 내보내기
CREATE TABLE IF NOT EXISTS `lol_player` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `puuid` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `summoner_name` varchar(50) DEFAULT NULL,
  `summoner_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `tier` varchar(50) DEFAULT NULL,
  `rank` varchar(50) DEFAULT NULL,
  `league_points` int DEFAULT NULL,
  `summoner_level` int DEFAULT NULL,
  `wins` int DEFAULT NULL,
  `losses` int DEFAULT NULL,
  `profile_icon` int DEFAULT NULL,
  `is_deleted` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `puuid` (`puuid`)
) ENGINE=InnoDB AUTO_INCREMENT=7992 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 내보낼 데이터가 선택되어 있지 않습니다.

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;

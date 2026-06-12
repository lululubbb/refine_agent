package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_5_6Test {

    @Test
    public void testisMapped_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, null, "comment", 1);
        Assertions.assertEquals(false, record.isMapped("name"), "Expected isMapped to return false when mapping is null");
    }

    @Test
    public void testisMapped_mappingDoesNotContainKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1);
        Assertions.assertEquals(false, record.isMapped("key2"), "Expected isMapped to return false for a non-existent key");
    }

    @Test
    public void testisMapped_mappingContainsKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1);
        Assertions.assertEquals(true, record.isMapped("key1"), "Expected isMapped to return true for an existing key");
    }

    @Test
    public void testisMapped_emptyMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1);
        Assertions.assertEquals(false, record.isMapped("key1"), "Expected isMapped to return false for an empty mapping");
    }

    @Test
    public void testisMapped_nullKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1);
        Assertions.assertEquals(false, record.isMapped(null), "Expected isMapped to return false for a null key");
    }

    @Test
    public void testisMapped_emptyStringKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1);
        Assertions.assertEquals(true, record.isMapped(""), "Expected isMapped to return true for an empty string key");
    }
}
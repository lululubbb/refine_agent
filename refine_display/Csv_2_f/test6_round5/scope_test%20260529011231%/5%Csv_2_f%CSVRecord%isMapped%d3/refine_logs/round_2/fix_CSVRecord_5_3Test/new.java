package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_5_3Test {

    @Test
    public void testisMapped_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, null, null, 1);
        Assertions.assertFalse(record.isMapped("testName"));
    }

    @Test
    public void testisMapped_keyExistsInMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("testName", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertTrue(record.isMapped("testName"));
        Assertions.assertEquals(true, record.isMapped("testName"));
    }

    @Test
    public void testisMapped_keyDoesNotExistInMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("otherName", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertFalse(record.isMapped("testName"));
        Assertions.assertEquals(false, record.isMapped("testName"));
    }

    @Test
    public void testisMapped_emptyMapping() throws Exception {
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertFalse(record.isMapped("testName"));
        Assertions.assertEquals(false, record.isMapped("testName"));
    }

    @Test
    public void testisMapped_mappingContainsDifferentKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("anotherName", 1);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertFalse(record.isMapped("testName"));
        Assertions.assertEquals(false, record.isMapped("testName"));
    }
}
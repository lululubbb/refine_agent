package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_5_2Test {

    @Test
    public void testisMapped_mappingIsNull() {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, null, "comment", 1L);
        Assertions.assertFalse(record.isMapped("name"));
    }

    @Test
    public void testisMapped_nameExistsInMapping() {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1L);
        Assertions.assertTrue(record.isMapped("name"));
    }

    @Test
    public void testisMapped_nameDoesNotExistInMapping() {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("otherName", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1L);
        Assertions.assertFalse(record.isMapped("name"));
    }

    @Test
    public void testisMapped_emptyMapping() {
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1L);
        Assertions.assertFalse(record.isMapped("name"));
    }

    @Test
    public void testisMapped_mappingIsNotNullAndEmpty() {
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1L);
        Assertions.assertFalse(record.isMapped("name"));
    }
}
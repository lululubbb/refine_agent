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

public class CSVRecord_5_1Test {

    @Test
    public void testisMapped_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, null, null, 1);
        Assertions.assertFalse(record.isMapped("name"));
    }

    @Test
    public void testisMapped_mappingContainsKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertTrue(record.isMapped("name"));
    }

    @Test
    public void testisMapped_mappingDoesNotContainKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("otherName", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertFalse(record.isMapped("name"));
    }

    @Test
    public void testisMapped_emptyMapping() throws Exception {
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertFalse(record.isMapped("name"));
    }
}
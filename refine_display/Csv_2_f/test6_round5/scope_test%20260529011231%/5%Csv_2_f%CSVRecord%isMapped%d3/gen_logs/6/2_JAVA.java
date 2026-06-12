package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.util.HashMap;
import java.util.Map;

public class CSVRecord_5_6Test {

    @Test
    public void testisMapped_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, null, "comment", 1);
        Assertions.assertFalse(record.isMapped("name"));
    }

    @Test
    public void testisMapped_mappingDoesNotContainKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1);
        Assertions.assertFalse(record.isMapped("key2"));
    }

    @Test
    public void testisMapped_mappingContainsKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1);
        Assertions.assertTrue(record.isMapped("key1"));
    }
}
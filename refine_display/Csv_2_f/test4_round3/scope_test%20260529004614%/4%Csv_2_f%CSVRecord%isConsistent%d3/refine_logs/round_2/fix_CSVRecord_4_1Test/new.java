package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_4_1Test {

    @Test
    public void testIsConsistent_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, null, null, 1);
        Assertions.assertEquals(true, record.isConsistent());
    }

    @Test
    public void testIsConsistent_mappingSizeEqualsValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertEquals(true, record.isConsistent());
    }

    @Test
    public void testIsConsistent_mappingSizeNotEqualsValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2); // Additional mapping to trigger inconsistency
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertEquals(false, record.isConsistent());
    }

    @Test
    public void testIsConsistent_emptyValues() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(new String[]{}, mapping, null, 1);
        Assertions.assertEquals(true, record.isConsistent());
    }

    @Test
    public void testIsConsistent_singleValueMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertEquals(true, record.isConsistent());
    }

    @Test
    public void testIsConsistent_multipleValueMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2", "value3"}, mapping, null, 1);
        Assertions.assertEquals(true, record.isConsistent());
    }
}
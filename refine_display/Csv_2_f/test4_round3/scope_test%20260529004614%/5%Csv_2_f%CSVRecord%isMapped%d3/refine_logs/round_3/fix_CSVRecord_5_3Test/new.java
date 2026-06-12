package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_5_3Test {

    @Test
    public void testisMapped_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, null, "comment", 1);
        Assertions.assertEquals(false, record.isMapped("name"));
    }

    @Test
    public void testisMapped_nameExistsInMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, "comment", 1);
        Assertions.assertEquals(true, record.isMapped("name"));
    }

    @Test
    public void testisMapped_nameDoesNotExistInMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("otherName", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, "comment", 1);
        Assertions.assertEquals(false, record.isMapped("name"));
    }

    @Test
    public void testisMapped_emptyMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, "comment", 1);
        Assertions.assertEquals(false, record.isMapped("name"));
    }

    @Test
    public void testisMapped_nullName() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, "comment", 1);
        Assertions.assertEquals(false, record.isMapped(null));
    }

    @Test
    public void testisMapped_emptyStringName() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, "comment", 1);
        Assertions.assertEquals(false, record.isMapped(""));
    }
}
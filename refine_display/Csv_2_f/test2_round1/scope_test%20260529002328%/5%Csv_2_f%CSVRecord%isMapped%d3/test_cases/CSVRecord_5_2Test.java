package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_5_2Test {

    @Test
    public void testisMapped_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, null, "comment", 1L);
        Assertions.assertEquals(false, record.isMapped("name"));
    }

    @Test
    public void testisMapped_nameExistsInMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1L);
        Assertions.assertEquals(true, record.isMapped("name"));
    }

    @Test
    public void testisMapped_nameDoesNotExistInMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("otherName", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1L);
        Assertions.assertEquals(false, record.isMapped("name"));
    }

    @Test
    public void testisMapped_emptyMapping() throws Exception {
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1L);
        Assertions.assertEquals(false, record.isMapped("name"));
    }

    @Test
    public void testisMapped_mappingIsNotNullAndEmpty() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, "comment", 1L);
        Assertions.assertEquals(false, record.isMapped("name"));
    }
}
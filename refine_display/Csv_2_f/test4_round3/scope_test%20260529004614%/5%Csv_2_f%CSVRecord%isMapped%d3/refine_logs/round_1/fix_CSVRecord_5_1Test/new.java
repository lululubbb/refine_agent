package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_5_1Test {

    @Test
    public void testisMapped_mappingIsNotNullAndContainsKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value"}, mapping, null, 1);

        boolean result = invokeIsMapped(record, "name");

        Assertions.assertEquals(true, result);
    }

    @Test
    public void testisMapped_mappingIsNotNullAndDoesNotContainKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value"}, mapping, null, 1);

        boolean result = invokeIsMapped(record, "otherName");

        Assertions.assertEquals(false, result);
    }

    @Test
    public void testisMapped_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value"}, null, null, 1);

        boolean result = invokeIsMapped(record, "name");

        Assertions.assertEquals(false, result);
    }

    private boolean invokeIsMapped(CSVRecord record, String name) throws Exception {
        return record.isMapped(name);
    }
}